import json, pystac


from typing import List
from app.aws.s_three import Collection as S3Collection, WarehouseClient, Resource
from app.config.S3Config import S3Config
from .TxItem import TxItem
from app.root import ROOT
# Import geographic manipulation libraries
import geopandas
from osgeo import gdal
from app.stac import log_info, log_exception
from pandas import DataFrame

from app.stac.pystac_extension.file_parsing import file_types
from app.stac.pystac_extension.TxTypes import TileIndexDict

BUILD_TEST_GEOJSON = True

gdal.UseExceptions()

class CollectionException(Exception):
    pass

class TxCollection(pystac.Collection):
    extra_fields = {}
    settings = {
        "LAZ_3D_BBOX":  True,
        "API_URL": "https://api.tnris.org"
    }
    panda_layer: geopandas.GeoDataFrame
    resolution: str
    root = ""
    s3_collection: S3Collection
    wh_client: WarehouseClient
    data_wh_configuration: S3Config
    index: TileIndexDict
    href: str
    spatial_extent: pystac.SpatialExtent
    assets: dict

    def __init__(self, data_wh_configuration, s3_collection, collection_name, stac_extensions):
        self.wh_client: WarehouseClient = WarehouseClient(data_wh_configuration)
        self.data_wh_configuration = data_wh_configuration
        self.s3_collection = s3_collection
        self.collection_name = collection_name
        self.stac_extensions = stac_extensions
        self.href = f"./catalog/{collection_name}/collection.json"

        # Configure panda_layer using geopandas, vsipathing capabilities.
        vsi_path = f"/vsizip/vsicurl/{self.wh_client.get_filename_path(self.s3_collection.index_asset[0].path)}"
        self.panda_layer = geopandas.GeoDataFrame.from_file(vsi_path, layer=0).to_crs("EPSG:4326")
        self.tile = self.panda_layer.to_dict()
        self.index: TileIndexDict = TileIndexDict(self.panda_layer)

        self.spatial_extent = pystac.SpatialExtent(self.panda_layer.total_bounds.tolist())
        self.construct_spatial_tags()        
        if(self.index):
            self.extra_fields["txgio:geometry"] = self.index.get('outline')

    def construct_spatial_tags(self):
        # Tag counties
        counties = geopandas.read_file(f"{ROOT}/txgio_extension/county_boundaries.geojson")
        counties_buffer = open(f"{ROOT}/txgio_extension/county_boundaries.geojson")
        counties_dict = json.load(counties_buffer)
        intersections = counties.intersects(self.index.simplify)
        spatial_tags = ""

        for i in range(len(intersections)):
            if(intersections[i]):
                spatial_tags += f",{counties_dict['features'][i]['properties']['CNTY_NM']}"

        # Tag cities
        cities = geopandas.read_file(ROOT / "txgio_extension" / "county_boundaries.geojson")
        cities_buffer = open(ROOT / "txgio_extension" / "TX_Cities.json")
        cities_dict = json.load(cities_buffer)
        intersections2 = cities.intersects(self.index.simplify)
        for i in range(len(intersections2)):
            if(intersections2[i]):
                spatial_tags += f",{cities_dict['objects']['TX_Cities']['geometries'][i]['properties']['name']}"
        try:
            if(BUILD_TEST_GEOJSON):
                with  open(f"{ROOT}/testgeojson/{self.root}_testgeom.geojson", "w") as f:
                    f.write(self.index.outline)
        except:
            log_info("Couldn't write an example geojson")

        self.extra_fields["txgio:spatial_keywords"] = spatial_tags[1:]

    def csv_to_arr(self, csv: str) -> list[str]:
        if(not csv or len(csv) < 1):
            return []

        vals = csv.split(',')
        for val in enumerate(vals):
            vals[val[0]-1] = vals[val[0]-1].strip()
        return vals

    def add_stac_items(self, resources: List[Resource]) -> pystac.Item | pystac.STACObject | None:
        """
        Docstring for add_stac_items
        
        :param self: Description
        :param resources: Description
        :type resources: List[Resource]
        :return: Description
        :rtype: Item | STACObject | None
        """
        tx_item = None
        sreference:str | list[str] | None = self.extra_fields.get("txgio:spatial_reference")

        try:
            tx_item = TxItem(resources,
                                sreference,
                                self.id,
                                self.tile,
                                self.resolution,
                                self.data_wh_configuration)
            tx_item.validate()
        except Exception as e:
            log_exception(e)
            return None
        
        if(tx_item and len(resources) and len(tx_item.links)):
            self.add_item(item=tx_item)
            return tx_item
        else:
            log_info(f"No known filetype for filename: {resources[0].filename}.")
            return None

    def build_stac_items(self):
        resources = []
        whc: DataFrame = DataFrame(data=self.s3_collection.paths.ITEMS)

        def build_asset_item(item, description, media_type, role):
            title = f"{self.root}-{item.ext.split('.')[-1]}"

            from app.stac.pystac_extension.file_parsing import file_types
            roles = file_types[item.ext]
            
            a = roles['description']
            b = roles['media_type']
            c = roles['usage']
            asset_item = pystac.ItemAssetDefinition({
                    "description": a,
                    "ext": item.ext,
                    "media_type": media_type,
                    "roles": [item.ext,b,c],
                    "title": title
                })
            self.item_assets[title] = asset_item

        for wh in whc.itertuples():
            item = wh[1]
            i = wh[0]
            next_index=None
            if(i+1 < len(whc.values)):
                next_index = whc.values[i+1][0].index
            resources.append(item)
            type = file_types[item.ext]
            build_asset_item(item, type.description, type.media_type, type.usage)

            # tx_collection.item_assets.update()
            if(item.index == next_index):
                #Proceed to add the next item to the resources array to combine into one item.
                continue
            self.add_stac_items(resources)
            resources = []