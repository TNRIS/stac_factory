from .pystac_extension.TxNewCollection import TxNewCollection
from .pystac_extension.TxOldCollection import TxOldCollection
from .pystac_extension.TxCatalog import TxCatalog

from app.stac import log_info
from pandas import DataFrame
from multiprocessing import Process, Queue
import os
import pystac
import time
from pypgstac.load import Loader, Methods
from pypgstac.db import PgstacDB
from pypgstac.load import Loader
from app.aws.s_three import WarehouseClient
from app.aws.s_three import Collection as S3Collection
import shutil
from app.root.root import ROOT

db = PgstacDB()
loader = Loader(db)
temp_storage = f"{ROOT}/catalog/" # Don't change this unless you know what it does. It will

# # Register the custom write method
# stac_io

#TODO
#Update stac catalog schema
#Make this use multiprocessing
class TestException(Exception):
    pass

# Toggle this to True in order to rebuild the catalog from scratch.
SKIP_KNOWN_COLLECTIONS_FLAG: bool = True # Set this to True.
CLEAN_STASH_FLAG = False

wh_client: WarehouseClient

def skipper(collection_root):
    #"stratmap-2019-address-points", # Well done
    if(collection_root in [
        "tlc-legislative-boundaries", # No index file.
        "stratmap-2026-city-boundaries", #STATE_FIPS is 48, but tileid is 48000
        "usgs-nhap-1981-cir-75cm", # Tile Index label is "Name", should be using TileID or something.
        "utbeg-geologic-atlas-250k", # Tile Index column label is "Name", and values are tile id's they are just text names, seems unstandard
        "stratmap-2021-nccir-6in-12in-caparea-brazos-kerr", ## Tile Index column label is "Name", and values are tile id's they are just text names, seems unstandard
        "txgio-rivers-streams-waterbodies", # Tile Index missing
        "noaa-2020-ccap-landcover-1m", # Multiple, problems, seems to be using  tile index of the -r one (noaa-2020-ccap-landcover-1m-r).
        "naip-2016-nccir-1m" #No TileID entry for Tile 2800641 in naip-2016-nccir
    ]):
        #log_info(f"Skipping {collection_root}")
        return True
    
    # if(not collection_root == "stratmap-2019-address-points"):
    #     log_info(f"Skipping {collection_root}")
    #     return True
    
    log_info(f"Running {collection_root}")
    
def build_collection(wh_collection, s3_configuration, q: Queue | None):
    wh_client = WarehouseClient(s3_configuration)
    collection_root = ""
    tx_collection: TxNewCollection | TxOldCollection
    s3_collection: S3Collection
    


    if(isinstance(wh_collection, str)):
        collection_root = wh_collection
        if(skipper(collection_root)):
            return
        if os.path.exists(f"{temp_storage}{collection_root}"):
            log_info(f"Skipping {collection_root} because it exists.")
            dest_href=f"{temp_storage}{collection_root}"
            if(q):
                q.put(dest_href)
            return True
        items = wh_client.get(f"{s3_configuration.ROOT}{collection_root}")
        s3_collection = S3Collection(items)
        if len(items):
            tx_collection = TxOldCollection(wh_collection, s3_collection, s3_configuration)
    else:
        collection_root = wh_collection['id']
        if(skipper(collection_root)):
            return
        items = wh_client.get(f"{s3_configuration.ROOT}{collection_root}")
        s3_collection = S3Collection(items)
        if len(items):
            tx_collection = TxNewCollection(wh_collection, s3_collection, s3_configuration)
    
    try:
        if(not s3_collection.paths.ASSETS):
            print(f"No asset for {collection_root}")
            return None
    except Exception as e:
        print(f"No asset for {collection_root}")
        return None

    for asset in s3_collection.paths.ASSETS:
        if asset.type == "index":
            passet = pystac.Asset(
                href=asset.path,
                media_type="text",
                extra_fields={
                    "file:size":asset.size,
                    "file:local_path":asset.path
                }
            )
            tx_collection.assets['tile_index_url'] = passet
        else:
            passet = pystac.Asset(
                href=f"{s3_configuration.BUCKET_URL}{asset.path}",
                media_type=asset.type,
                extra_fields={
                    "file:size":asset.size,
                    "file:local_path":asset.path
                }
            )
            tx_collection.assets[asset.fname] = passet

    try:
        log_info(f"Validating {collection_root}")
        tx_collection.validate()
        log_info(f"Done validating {collection_root}")
    except Exception as e:
        log_info(f"Invalid document {collection_root}")
        return

    tx_collection.save(dest_href=dest_href)

    if(q):
        q.put(dest_href)
    return tx_collection

def clean_stash():
    if(CLEAN_STASH_FLAG):
        if(os.path.exists(temp_storage)):
            shutil.rmtree(temp_storage)

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

    # Build a list of processes, to be ran at a later time.
    for whcollection in wh_collections.itertuples():
        p = Process(name=whcollection[1], target=build_collection, args=(whcollection[1].split('/')[-2], whc, q))
        if(not p):
            continue
        tasks.append(p)

    MAX_PROCS = 8
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

    collections = []

    while(not q.empty()):
        collection = q.get()
        collections.append(pystac.read_file(f"{collection}/collection.json"))

    catalog.add_children(collections)
    catalog.save_object(dest_href=temp_storage)
    log_info("Done processing.")
def gen_this_stac_collection(whc, s3_configuration):
    """
    Gather the directory structure of the TNRIS data warehouse using the WarehouseClient.
    """
    clean_stash()
    SKIP_KNOWN_COLLECTIONS_FLAG = False
    tx_collection = build_collection(whc, s3_configuration)
    # tx_collection.validate()
    if(tx_collection):

    # print("Validating items") --- I'm going to upload the export I sent you guys to test it.
    # tx_collection.validate_all()
    # print("Items Valid")
        collections = [tx_collection.to_dict()]
        dict_items = tx_collection.get_items()
        loader.load_collections(collections, insert_mode=Methods.upsert)
        items = []
        for i in dict_items:
            items.append(i.to_dict())
        loader.load_items(items, insert_mode=Methods.upsert)
