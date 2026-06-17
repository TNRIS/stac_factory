from .pystac_extension.TxNewCollection import TxNewCollection
from .pystac_extension.TxOldCollection import TxOldCollection


from app.stac import log_info
from pandas import DataFrame
from multiprocessing import Process
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
temp_storage = f"{ROOT}/collections/" # Don't change this unless you know what it does. It will

# # Register the custom write method
# stac_io

#TODO
#Update stac catalog schema
#Make this use multiprocessing
class TestException(Exception):
    pass

# Toggle this to True in order to rebuild the catalog from scratch.
SKIP_KNOWN_COLLECTIONS_FLAG: bool = True # Set this to True.
CLEAN_STASH_FLAG = True

wh_client: WarehouseClient
def build_collection(wh_collection, s3_configuration):
    wh_client = WarehouseClient(s3_configuration)
    collection_root = ""
    tx_collection: TxNewCollection | TxOldCollection
    s3_collection: S3Collection
    if(isinstance(wh_collection, str)):
        collection_root = wh_collection
        items = wh_client.get(f"{s3_configuration.ROOT}{collection_root}")
        s3_collection = S3Collection(items)
        if len(items):
            tx_collection = TxOldCollection(wh_collection, s3_collection, s3_configuration)
    else:
        collection_root = wh_collection['id']
        items = wh_client.get(f"{s3_configuration.ROOT}{collection_root}")
        s3_collection = S3Collection(items)
        if len(items):
            tx_collection = TxNewCollection(wh_collection, s3_collection, s3_configuration)

    if(collection_root in [
        #"stratmap-2019-address-points", # Well done
        "usgs-nhap-1981-cir-75cm",
        "stratmap-2021-nccir-6in-12in-caparea-brazos-kerr",
        "stratmap-2026-city-boundaries", #STATE_FIPS is 48, but tileid is 48000
        #"noaa-2020-ccap-landcover-1m" # Multiple,
        "noaa-2020-ccap-landcover-1m-r" # Only has index 11111
    ]):
        log_info(f"Skipping {collection_root}")
        return
    
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

    tx_collection.save(dest_href=f"{temp_storage}/{collection_root}")
    return tx_collection

    
MAX_PROCESSES = 5
running_processes = 0
processes: list[Process] = []

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
    for whcollection in wh_collections.itertuples():
        global MAX_PROCESSES, processes
        
        p = Process(name=whcollection[1], target=build_collection, args=(whcollection[1].split('/')[-2], whc))
        if(not p):
            continue
        # p.start()
        # p.join()

        if(len(processes) < MAX_PROCESSES):
            
            log_info(f"Starting a new Process. processes = {len(processes)}")
            p.start()
            processes.append(p)
        else:
            AWAIT = True
            while(AWAIT):
                for i, process in enumerate(processes):
                    if(not process.is_alive()):
                        AWAIT = False

                        log_info("Joining a new process.")
                        processes.pop(i)
                        process.join()
                        p.start()
                        processes.append(p)

                time.sleep(5)
            

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
