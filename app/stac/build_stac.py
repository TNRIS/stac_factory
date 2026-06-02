
from app.aws.s_three import Collection as S3Collection, WarehouseClient, Resource
from app.config import DATA_WH_CONF_HISTORIC, DATA_WH_CONF
from .pystac_extension.TxCollection import TxCollection
from pandas import DataFrame
from multiprocessing import Process
import os
import pystac
from pypgstac.load import Loader, Methods
from pypgstac.db import PgstacDB
from pypgstac.load import Loader

db = PgstacDB()
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

wh_client: WarehouseClient
def build_collection(wh_collection, s3_configuration):
    wh_client = WarehouseClient(s3_configuration)
    collection_root = wh_collection['id']
    if(collection_root == "usgs-nhap-1981-cir-75cm"):
        print(f"Skipping {collection_root}")
        return
    FILE_DIR = f"/root/workspace/stac_factory/catalog/{collection_root}/collection.json"
    FILE_NOT_FOUND = not os.path.exists(FILE_DIR)

    # Loop through each collection.
    if(FILE_NOT_FOUND and SKIP_KNOWN_COLLECTIONS_FLAG):
        items = wh_client.get(f"{s3_configuration.ROOT}{collection_root}")
        if len(items):
            s3_collection = S3Collection(items)

            tx_collection = None
            tx_collection = TxCollection(collection_root, s3_collection, s3_configuration)
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
                
                tx_collection.save(dest_href=f"/root/workspace/stac_factory/catalog/{collection_root}")
            return tx_collection
        else:
            print(f"There are no items or assets accessible for the collection: {collection_root}")

    else:
        tx_collection = pystac.read_file(f"/root/workspace/stac_factory/catalog/{collection_root}/collection.json")        
        return tx_collection
    

def gen_stac_collection() -> None:
    """
    Docstring for gen_stac_item
    Switch between data types and generate a stack item. GENERATES ALL COLLECTIONS IN S3.
    """
    wh_client = WarehouseClient(DATA_WH_CONF)
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

def gen_this_stac_collection(whc, s3_configuration):
    """
    Gather the directory structure of the TNRIS data warehouse using the WarehouseClient.
    """
    tx_collection = build_collection(whc, s3_configuration)
    collections = [tx_collection.to_dict()]
    dict_items = tx_collection.get_items()
    
    loader.load_collections(collections, insert_mode=Methods.upsert)
    items = []
    for i in dict_items:
        items.append(i.to_dict())
    loader.load_items(items, insert_mode=Methods.upsert)


