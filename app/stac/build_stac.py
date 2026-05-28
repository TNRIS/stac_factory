from ast import arg
from encodings import undefined
from numbers import Number

import pypgstac.db
import pypgstac.pypgstac
from aws.s_three import Collection as S3Collection, WarehouseClient, Resource
from config import DATA_WH_CONF_HISTORIC, DATA_WH_CONF
from .pystac_extension.TxCollection import TxCollection
from pandas import DataFrame
from multiprocessing import Process
import shutil
import os, gc
import pystac
import time
from pypgstac.load import Loader, Methods, Partition
from pypgstac.db import PgstacDB
from pypgstac.load import Loader
from pathlib import Path

# DSN can also come from environment variables
dsn = undefined

db = PgstacDB(dsn)
loader = Loader(db)

# # Register the custom write method
# stac_io

#TODO
#Update stac catalog schema
#Make this use multiprocessing
class TestException(Exception):
    pass

# Toggle this to True in order to rebuild the catalog from scratch.
SKIP_KNOWN_COLLECTIONS_FLAG = True # Set this to True.

wh_client: WarehouseClient = WarehouseClient(DATA_WH_CONF)
def build_collection(wh_collection):
    wh_collection = wh_collection
    collection_root = wh_collection.split('/')[-2]
    if(collection_root == "usgs-nhap-1981-cir-75cm"):
        print(f"Skipping {collection_root}")
        return
    FILE_DIR = f"./catalog/{collection_root}/collection.json"
    FILE_NOT_FOUND = not os.path.exists(FILE_DIR)

    # Loop through each collection.
    if(FILE_NOT_FOUND and SKIP_KNOWN_COLLECTIONS_FLAG):
        items = wh_client.get(wh_collection)
        if len(items):
            s3_collection = S3Collection(items)

            tx_collection = None
            tx_collection = TxCollection(collection_root, s3_collection)
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
                        href=f"{DATA_WH_CONF.BUCKET_URL}{asset.path}",
                        media_type=asset.type,
                        extra_fields={
                            "file:size":asset.size,
                            "file:local_path":asset.path
                        }
                    )

                    tx_collection.assets[asset.fname] = passet
                
                tx_collection.save(dest_href=f"/root/workspace/app/catalog/{collection_root}")
            return tx_collection.to_dict()
        else:
            print(f"There are no items or assets accessible for the collection: {collection_root}")

    else:
        tx_collection = pystac.read_file(FILE_DIR)
        dict = tx_collection.to_dict()
        # stac_catalog.add_child(tx_collection)
        dict_items = tx_collection.get_items()
        items = []
        for i in dict_items:
            items.append(i.to_dict())
        loader.load_items(items, insert_mode=Methods.upsert)
        
        return tx_collection.to_dict()
    

def gen_stac_collection() -> None:
    """
    Docstring for gen_stac_item
    Switch between data types and generate a stack item. GENERATES ALL COLLECTIONS IN S3.
    """
    wh_collections = DataFrame(wh_client.get_collections())
    processes = []

    for whc in wh_collections.itertuples():
        p = Process(name=whc[1], target=build_collection, args=([whc[1]]))
        if(not p):
            continue
        p.start()
        processes.append(p)

    for process in processes:
        process.join()

def gen_this_stac_collection(whc):
    """
    Gather the directory structure of the TNRIS data warehouse using the WarehouseClient.
    """
    collections = []
    collections.append(build_collection(whc))
    loader.load_collections(collections, insert_mode=Methods.upsert)