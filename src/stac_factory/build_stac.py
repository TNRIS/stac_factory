from multiprocessing import Process, Queue
from pandas import DataFrame
import os, pystac, time, shutil

from .root import ROOT, CATALOG_ROOT
from ._internal.tx_pystac.tx_types import ContentInput
from ._internal.util import log_info
from ._internal import (
    TxNewCollection,
    TxOldCollection,
    TxLoader,
    TxCatalog,
    build_roles_for,
    WarehouseClient,
    Collection as S3Collection
)

loader = TxLoader()
# # Register the custom write method
# stac_io


class TestException(Exception):
    pass


# Toggle this to True in order to rebuild the catalog from scratch.
SKIP_KNOWN_COLLECTIONS_FLAG: bool = True  # Set this to True.
CLEAN_STASH_FLAG = True

wh_client: WarehouseClient


def skipper(collection_root):
    if collection_root in [
        "tlc-legislative-boundaries",  # No index file.
        "stratmap-2026-city-boundaries",  # STATE_FIPS is 48, but tileid is 48000
        "usgs-nhap-1981-cir-75cm",  # Tile Index label is "Name", should be using TileID or something.
        "utbeg-geologic-atlas-250k",  # Tile Index column label is "Name", and values are tile id's they are just text names, seems unstandard
        "stratmap-2021-nccir-6in-12in-caparea-brazos-kerr",  ## Tile Index column label is "Name", and values are tile id's they are just text names, seems unstandard
        "txgio-rivers-streams-waterbodies",  # Tile Index missing
        "noaa-2020-ccap-landcover-1m",  # Multiple, problems, seems to be using  tile index of the -r one (noaa-2020-ccap-landcover-1m-r).
        "naip-2016-nccir-1m",  # No TileID entry for Tile 2800641 in naip-2016-nccir
    ]:
        return True

    log_info(f"Running {collection_root}")


def build_collection(
    wh_collection, s3_configuration, q: Queue | None = None
) -> None | TxOldCollection | TxNewCollection:
    wh_client = WarehouseClient(s3_configuration)
    collection_root = ""
    tx_collection: TxNewCollection | TxOldCollection
    s3_collection: S3Collection
    dest_href = ""
    if isinstance(wh_collection, str):
        collection_root = wh_collection
        dest_href = f"{CATALOG_ROOT}/{collection_root}"

        if skipper(collection_root):
            return
        if os.path.exists(dest_href):
            log_info(f"Skipping {collection_root} because it exists.")

            q.put(dest_href)
            return None
        items = wh_client.get(f"{s3_configuration.ROOT}{collection_root}")
        s3_collection = S3Collection(items)
        if len(items):
            tx_collection = TxOldCollection(
                wh_collection, s3_collection, s3_configuration
            )
    else:
        collection_root = wh_collection["id"]
        dest_href = f"{CATALOG_ROOT}{collection_root}"
        if skipper(collection_root):
            return
        items = wh_client.get(f"{s3_configuration.ROOT}{collection_root}")
        s3_collection = S3Collection(items)
        if len(items):
            tx_collection = TxNewCollection(
                wh_collection, s3_collection, s3_configuration
            )

    try:
        if not s3_collection.paths.ASSETS:
            print(f"No asset for {collection_root}")
            return None
    except Exception as e:
        print(f"No asset for {collection_root}")
        return None

    for asset in s3_collection.paths.ASSETS:
        roles = build_roles_for(asset)
        if asset.type == "index":
            passet = pystac.Asset(
                href=asset.path,
                media_type="text",
                extra_fields={"file:size": asset.size, "file:local_path": asset.path},
                roles=roles,
            )
            tx_collection.assets["tile_index_url"] = passet
        else:
            passet = pystac.Asset(
                href=f"{s3_configuration.BUCKET_URL}{asset.path}",
                media_type=asset.type,
                extra_fields={"file:size": asset.size, "file:local_path": asset.path},
                roles=roles,
            )
            tx_collection.assets[asset.fname] = passet

    try:
        log_info(f"Validating {collection_root}")
        tx_collection.validate_all()
        tx_collection.save(dest_href=dest_href)
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
                time.sleep(0.05)

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
        collections.append(pystac.read_file(f"{collection}/collection.json"))

    catalog.add_children(collections)
    catalog.normalize_and_save(root_href=CATALOG_ROOT)
    log_info("Done processing.")


def gen_this_stac_collection(whc: ContentInput, s3_configuration):
    """
    Gather the directory structure of the TNRIS data warehouse using the WarehouseClient.
    """
    clean_stash()
    content = loader.get_content(whc.get("id"))
    if content:
        # Exists so stash fastapi Metadata. (Only ran on edgecase we need to rebuild geometry or add items.)
        whc = content

    tx_collection = build_collection(whc, s3_configuration)
    if tx_collection:
        try:
            log_info("Validating items")
            tx_collection.validate_all()
        except Exception as e:
            log_info(f"Cannot validate {whc.id}")
            return

        catalog = TxCatalog()
        catalog.add_children([tx_collection])
        catalog.normalize_and_save(root_href=str(CATALOG_ROOT))
        dict_items = tx_collection.get_items()
        loader.load_collection_and_items(file=tx_collection, dict_items=dict_items)
