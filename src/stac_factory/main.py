from multiprocessing import Process, Queue
from pandas import DataFrame
from pathlib import Path
import os, pystac, time, shutil

from stac_factory.root import ROOT, CATALOG_ROOT
from stac_factory._internal.tx_pystac.tx_types import ContentInput
from stac_factory._internal.util import log_info
from stac_factory._internal import (
    TxNewCollection,
    TxOldCollection,
    TxLoader,
    TxCatalog,
    RoleBuilder,
    WarehouseClient,
    LocalWarehouseClient,
    S3Collection,
)

# Toggle this to True in order to rebuild the catalog from scratch.
SKIP_KNOWN_COLLECTIONS_FLAG: bool = True  # Set this to True.
CLEAN_STASH_FLAG = True

loader = TxLoader()

# # Register the custom write method
# stac_io


class TestException(Exception):
    pass


wh_client: WarehouseClient


def skipper(collection_root):
    if collection_root in [
        "tlc-legislative-boundaries",  # No index file.
        # "stratmap-2026-city-boundaries",
        "usgs-nhap-1981-cir-75cm",
        # "utbeg-geologic-atlas-250k",
        # "stratmap-2021-nccir-6in-12in-caparea-brazos-kerr",
        # "txgio-rivers-streams-waterbodies",  # Tile Index missing
        # "naip-2016-nccir-1m",
        # "stratmap-2023-sanjac-river-ship-channels-bathy",
        "usace-2018-buffalo-bayou",
        # "noaa-2020-ccap-landcover-1m", # Has 11111 item in it
    ]:
        return True

    # For a quick test uncomment this if statement. It will test one collection.
    # if not collection_root == "stratmap-2026-city-boundaries":
    #     return True

    log_info(f"Running {collection_root}")


def build_collection(
    wh_collection,
    configuration,
    q: Queue | None = None,
) -> None | TxOldCollection | TxNewCollection:

    #
    # Determine storage backend
    #
    is_s3 = hasattr(configuration, "LOCAL") and not configuration.LOCAL

    def get_asset_href(path):
        if is_s3:
            return f"{configuration.BUCKET_URL}/{path}"

        return Path(path).relative_to("/").as_posix()

    wh_client = (
        WarehouseClient(configuration)
        if is_s3
        else LocalWarehouseClient(configuration)
    )

    collection_root = ""
    tx_collection: TxNewCollection | TxOldCollection
    warehouse_collection = None
    dest_href = ""

    if isinstance(wh_collection, str):
        collection_root = wh_collection
        dest_href = f"{CATALOG_ROOT}/{collection_root}/"

        # if skipper(collection_root):
        #     return

        items = wh_client.get(f"{configuration.ROOT}/{collection_root}")
        warehouse_collection = S3Collection(items)

        if len(items):
            tx_collection = TxOldCollection(
                wh_collection,
                warehouse_collection,
                configuration,
            )

    else:
        collection_root = wh_collection["id"]
        dest_href = f"{CATALOG_ROOT}/{collection_root}/"

        if skipper(collection_root):
            return

        items = wh_client.get(f"{configuration.ROOT}/{collection_root}")
        warehouse_collection = S3Collection(items)

        if len(items):
            tx_collection = TxNewCollection(
                wh_collection,
                warehouse_collection,
                configuration,
                is_s3=is_s3
            )

    try:
        if not warehouse_collection.paths.ASSETS:
            log_info(
                f"No asset for {collection_root}. "
                "Because no assets are found."
            )
            return None

    except Exception as e:
        log_info(f"No asset for {collection_root}")
        log_info(f"Invalid document {collection_root}", e)
        return None

    #
    # Asset generation
    #
    for asset in warehouse_collection.paths.ASSETS:

        builder = RoleBuilder(
            configuration.BUCKET_URL if is_s3 else ""
        )

        roles = builder.build_roles_for(asset, is_s3)
        asset_href = get_asset_href(asset.path)

        # local_href should not be different than asset_href if we are running this as a validator.
        local_href = asset_href
        if(is_s3):
            local_href = asset.path
        if asset.type == "index":
            passet = pystac.Asset(
                href=asset_href,
                media_type="text",
                extra_fields={
                    "file:size": asset.size,
                    "file:local_path": local_href,
                },
                roles=roles,
            )

            tx_collection.assets["tile_index_url"] = passet

        else:
            passet = pystac.Asset(
                href=asset_href,
                media_type=asset.type,
                extra_fields={
                    "file:size": asset.size,
                    "file:local_path": local_href,
                },
                roles=roles,
            )

            tx_collection.assets[asset.fname] = passet

    try:
        log_info(f"Validating {collection_root}")

        tx_collection.validate_all()
        tx_collection.normalize_and_save(root_href=dest_href)

        log_info(f"Done validating {collection_root}")

    except Exception as e:
        log_info(f"Invalid document {collection_root}")
        return None

    if q:
        q.put(dest_href)

    return tx_collection

def clean_stash():
    if CLEAN_STASH_FLAG:
        if os.path.exists(CATALOG_ROOT):
            shutil.rmtree(CATALOG_ROOT)


def gen_stac_collection(whc) -> None:
    """
    Docstring for gen_stac_item
    Switch between data types and generate a stack item. GENERATES ALL COLLECTIONS IN S3.
    """
    clean_stash()
    wh_client = WarehouseClient(whc)
    wh_collections = DataFrame(wh_client.get_collections())
    catalog = TxCatalog()
    q = Queue()
    tasks: list = []

    try:
        # Build a list of processes, to be ran at a later time.
        for whcollection in wh_collections.itertuples():
            p = Process(
                name=whcollection[1],
                target=build_collection,
                args=(whcollection[1].split("/")[-2], whc, q),
            )

            tasks.append(p)

        MAX_PROCS = min(
            os.cpu_count(), 16
        )  # Max 16 processes at once TODO: Calculate ram in Gigabytes and divide by 1.3
        running = []

        for task in tasks:
            # Wait until there's a free slot
            while len(running) >= MAX_PROCS:
                for p in list(running):
                    if not p.is_alive():
                        p.join()
                        running.remove(p)
                time.sleep(0.01)

            # Start a new process
            task.start()
            running.append(task)

        # Final cleanup (wait for remaining processes)
        for p in running:
            p.join()
    finally:
        for p in running:
            p.terminate()
            p.join()

    collections = []

    while not q.empty():
        collection = q.get()
        collection = pystac.read_file(f"{collection}/collection.json")

        for link in collection.links:
            link.resolve_stac_object(root=collection)

        collections.append(collection)

    catalog.add_children(collections)
    catalog.make_all_asset_hrefs_absolute()
    catalog.normalize_and_save(root_href=str(CATALOG_ROOT))
    log_info("Done processing.")


def gen_this_stac_collection(content_input: ContentInput, s3_configuration):
    """
    Gather the directory structure of the TNRIS data warehouse using the WarehouseClient.
    """
    clean_stash()
    # content = loader.get_content(content_input.get("id"))
    # if content:
    #     # Exists so stash fastapi Metadata. (Only ran on edgecase we need to rebuild geometry or add items.)
    #     content_input = content

    tx_collection = build_collection(content_input, s3_configuration)
    if tx_collection:
        try:
            log_info("Validating items")
            tx_collection.validate_all()
        except Exception as e:
            log_info(f"Cannot validate {content_input.id}")
            return

        log_info("Constructing catalog.")
        catalog = TxCatalog()
        log_info("Done constructing catalog starting to add items")
        catalog.add_children([tx_collection])
        log_info("Done adding items.")
        catalog.normalize_and_save(root_href=str(CATALOG_ROOT))

        log_info("Done normalizing and saving Getting items")
        dict_items = tx_collection.get_items()

        log_info("Done getting items. Calling pypgstac loader")
        loader.load_vanilla(file=tx_collection, dict_items=dict_items)
        log_info("Done calling pypgstac loader and done with program. SUCCESS")


def gen_local_stac_collection(
    content_input: ContentInput,
    local_configuration,
):
    """
    Generate a STAC collection from data stored in the local data warehouse.

    The collection is built from assets and items discovered on the local
    filesystem, validated, written to the catalog, and loaded into pgSTAC.
    """

    clean_stash()

    tx_collection = build_collection(
        content_input,
        local_configuration,
    )

    if not tx_collection:
        log_info(f"Unable to build collection: {content_input.get("id")}")
        return

    try:
        log_info("Validating collection items")
        tx_collection.validate_all()

    except Exception as e:
        log_info(f"Validation failed for collection {content_input.get("id")}: {e}")
        return

    log_info("Constructing catalog")

    catalog = TxCatalog()

    log_info("Adding collection to catalog")

    catalog.add_children
    print("Here")
