import shapely, pdal, os, json, pystac, requests

from datetime import datetime
from typing import Any, List
from app.aws.s_three import Collection as S3Collection, WarehouseClient, Resource
from .TxItem import TxItem
from app.root import ROOT
# Import geographic manipulation libraries
import geopandas as gpd
import pandas as pd
from osgeo import gdal
from .TxExtent import TxExtent
from app.stac import log_info, log_exception, stream_handler
from pandas import DataFrame
import time
from app.config import PathTyping

# Toggle this to True in order to rebuild the catalog from scratch.
COMPLETE_REBUILD_FLAG = False

gdal.UseExceptions()

class CollectionException(Exception):
    pass

class TxCollection(pystac.Collection):
    extra_fields = {}
    settings = {
        "LAZ_3D_BBOX":  True,
        "API_URL": "https://api.tnris.org"
    }
    panda_layer: dict | None = None
    resolution: str | None = None
    root = ""
    s3_collection: S3Collection

    def __init__(
        self,
        root: str | PathTyping.DataWhPath,
        s3_collection: S3Collection,
        data_wh_configuration,
        stac_extensions: list[str] = ["https://gist.githubusercontent.com/L-Har/b7b9018b31d1d8f17b7fc0c0dcb606c7/raw/36a2a0faf99139a499df6a51c0feb42a1c49fba3/txgio.json",
                                      "https://stac-extensions.github.io/file/v2.1.0/schema.json"]):
        """
        Docstring for __init__
        
        :param self: Pystac Collection TxCollection. It adds in defaults, and a constructor for a collection.
        :param stac_extensions: List of references to Stac Extensions. Default is fine for TxGIO. Override if needed.
        :type stac_extensions: list[str]
        """
        self.root = root
        self.s3_collection = s3_collection
        self.wh_client: WarehouseClient = WarehouseClient(data_wh_configuration)
        self.data_wh_configuration = data_wh_configuration

        href = f"./catalog/{root}/collection.json"
        print(f"Starting collection {root}")
        # Default extents. (Required for constructor)
        extents = TxExtent()
            
        #Run the cross walk function.
        coll_api = None
        if(isinstance(data_wh_configuration, str)):
            if '/historic/' in self.wh_client.root:
                coll_api = self.lore_xwalk(root)
            elif '/general/' in self.wh_client.root:
                coll_api = self.lcd_xwalk(root)
        
        if(not coll_api or not len(coll_api['results'])):
            return None #Nothing found in xwalk file, or otherwise.
        
        self.geo = None
        self.s3_key = root
        index = self.get_tile_index_collectionwide_data(s3_collection.index_asset[0].path)

        # Get max date
        # latest_date = pd.to_datetime('19700101') # Default to start of 1970
        # for stamp in index.get('dict').get('SrcImgDate').values():
        #     if(latest_date < pd.to_datetime(stamp)):
        #         latest_date = pd.to_datetime(stamp)
        coll_api = coll_api["results"][0]
        if index:
            if ('VerDate' in index.get('dict')):
                extents.temporal = pystac.TemporalExtent([datetime.fromisoformat(index.get('dict').get('VerDate')), datetime.fromisoformat(index.get('dict').get('VerDate'))])
            elif ('acquisition_date' in coll_api):
                extents.temporal = pystac.TemporalExtent([datetime.fromisoformat(coll_api.get('acquisition_date')), datetime.fromisoformat(coll_api.get('acquisition_date'))])
            else:
                extents.temporal = pystac.TemporalExtent([datetime.fromisoformat('0001-01-01'), datetime.fromisoformat('0001-01-01')])
            self.geo = shapely.from_geojson(json.dumps(index.get('convex_hull_polygon')))
            extents.spatial = pystac.SpatialExtent([self.geo.bounds[0], self.geo.bounds[1], self.geo.bounds[2], self.geo.bounds[3]])
            
        description = coll_api.get("description")
        if not description:
            description = coll_api.get("about")
        super(TxCollection, self).__init__(id=root, description=description, stac_extensions=stac_extensions, href=href, extent=extents, catalog_type = pystac.CatalogType.SELF_CONTAINED)
        if(index):
            self.extra_fields["txgio:geometry"] = index.get('convex_hull_polygon')

        self.__set_collection_meta_data(coll_api)
        self.build_stac_items()
   
    def lcd_xwalk(self, name):
        coll_api_url = f'{self.settings["API_URL"]}/api/v1/collections?s_three_key={name}'
        coll_api = requests.get(coll_api_url).json()

        if(len(coll_api['results'])):
            return coll_api
        else:
            cross_walk = pd.read_excel('txgio_extension/API-CollectionID-CollectionName-Crosswalk.xlsx', ["LCD"])["LCD"]
            
            for i in cross_walk.itertuples():
                if i[5] == name:
                    coll_api_url = f'{self.settings["API_URL"]}/api/v1/collections?s_three_key={i[4]}'
                    return requests.get(coll_api_url).json()
            
    def lore_xwalk(self, name):
        coll_api_url = ""
        coll_api = ""

        try:
            coll_api_url = f'{self.settings["API_URL"]}/api/v1/historical/collections?collection_id={name}'
            return requests.get(coll_api_url).json()
        except Exception as e:
            print(e)
        
        cross_walk = pd.read_excel('txgio_extension/API-CollectionID-CollectionName-Crosswalk.xlsx', ["LORE"])["LORE"]
        for i in cross_walk.itertuples():
            if i[8] == name:
                coll_api_url = f'{self.settings["API_URL"]}/api/v1/historical/collections?collection_id={i.collection_id}'
                return requests.get(coll_api_url).json()

    def add_stac_items(self, resources: List[Resource], coll_name, REBUILD_FLAG=False) -> pystac.Item | pystac.STACObject | None:
        """
        Docstring for add_stac_items: Just adds stac items from a resource. 
        
        :param self: Description
        :param resource: Description
        :type resource: Resource
        :param REBUILD_FLAG: Defaults to loading cached file.
        :return: Description
        :rtype: Item | STACObject | None
        """
        FIRST_RESOURCE = resources[0]
        ITEM_NAME = f"{coll_name}_{FIRST_RESOURCE.index}"

        FILE_DIR = f"./catalog/{coll_name}/{ITEM_NAME}/{ITEM_NAME}.json"
        FILE_NOT_FOUND = not os.path.exists(FILE_DIR)
        FILE_INVALID = False
            
        if(FILE_NOT_FOUND or REBUILD_FLAG):
            tx_item = None
            try:
                tx_item = TxItem(resources, self.extra_fields.get("txgio:spatial_reference"), self.id, self.tile, self.resolution, self.data_wh_configuration)
            except Exception as e:
                print(e)
                return None
            if(tx_item and len(resources) and len(tx_item.links)):
                self.add_item(item=tx_item)
                return tx_item
            else:
                log_info(f"No known filetype for filename: {resources[0].filename}.")
                return None
        else:
            # Else we load the item from the cache.
            try:
                tx_item = pystac.read_file(FILE_DIR)
                self.add_item(item=tx_item, title=self.id)
                return tx_item
            except Exception as e:
                log_info(f"No known filetype or a locally cached stac file for filename: {resources[0].filename}.")
                return None

    def csv_to_arr(self, csv: str) -> list[str]:
        if(not csv or len(csv) < 1):
            return []

        vals = csv.split(',')
        for val in enumerate(vals):
            vals[val[0]-1] = vals[val[0]-1].strip()
        return vals
    
    def __set_collection_meta_data(self, coll_api: dict):
        """
        Docstring for set_collection_meta_data
        
        :param self: Stac Builder
        """
        categories = self.csv_to_arr(coll_api['category'])

        for i, category in enumerate(categories):
            if category == "Lidar":
                categories[i] = "Elevation"
            elif category == "Land_Cover":
                categories[i] = "Basemap"
            
        self.extra_fields["txgio:categories"] = categories
        self.extra_fields["txgio:collection_id"] = coll_api["collection_id"]
        self.extra_fields["txgio:publication_date"] = coll_api["publication_date"]
        self.extra_fields["txgio:notes"] = coll_api['known_issues'] or '' # Use remarks in historic collections.
        self.extra_fields["txgio:spatial_reference"] = self.csv_to_arr(coll_api["spatial_reference"])
        self.extra_fields["txgio:resolution"] = coll_api["resolution"]
        self.extra_fields["txgio:bands"] = self.csv_to_arr(coll_api["band_types"])
        self.extra_fields["txgio:citation"] = "PLACEHOLDER"
        self.extra_fields["txgio:s_three_bucket_key"] = self.s3_key
        self.extra_fields["txgio:public"] = coll_api["public"]
        self.extra_fields["txgio:availability"] = coll_api["availability"] == "Download"
        self.extra_fields["txgio:banner_text"] = "PLACEHOLDER"
        self.extra_fields["txgio:last_modified"] = "1970-01-01"
        self.extra_fields["txgio:last_edited_by"] = "Placeholder"
        self.extra_fields["txgio:template"] = coll_api["template"]

        # Tag counties
        counties = gpd.read_file(f"{ROOT}/txgio_extension/county_boundaries.geojson")
        counties_buffer = open(f"{ROOT}/txgio_extension/county_boundaries.geojson")
        counties_dict = json.load(counties_buffer)
        intersections = counties.intersects(self.geo)
        spatial_tags = ""

        start = time.time()

        for i in range(len(intersections)):
            if(intersections[i]):
                spatial_tags += f",{counties_dict['features'][i]['properties']['CNTY_NM']}"
    
        self.extra_fields["txgio:spatial_keywords"] = spatial_tags[1:]

        # Tag cities
        cities = gpd.read_file(ROOT / "txgio_extension" / "county_boundaries.geojson")
        cities_buffer = open(ROOT / "txgio_extension" / "TX_Cities.json")
        cities_dict = json.load(cities_buffer)
        intersections2 = cities.intersects(self.geo)
        for i in range(len(intersections2)):
            if(intersections2[i]):
                spatial_tags += f",{cities_dict['objects']['TX_Cities']['geometries'][i]['properties']['name']}"
        
        end = time.time()

        print(f"intersections took {end - start} seconds.")

        self.license = coll_api["license_abbreviation"]
        self.license = coll_api["license_abbreviation"] if coll_api["license_abbreviation"] else "other"

        if(coll_api["thumbnail_image"]):
            thumbnail_image = pystac.Asset(
                href=coll_api["thumbnail_image"],
                media_type="text"
            )
            self.add_asset("thumbnail_image", thumbnail_image)

        if(coll_api["images"]):
            images = pystac.Asset(
                href=coll_api["images"],
                media_type="text"
            )
            self.add_asset("images", images)

        # Convert csv and category into a array. I chose to do it this way because it captures csv's with a space, and without.
        #Setup providers
        txGIO = pystac.Provider(name="TxGIO", url="https://geographic.texas.gov/", description="Texas Geographic Information Office")
        self.providers = [txGIO]
        if(coll_api["partners"] and (not (coll_api['partners'] == 'Texas Water Development Board/TxGIO'))):
            self.providers.append(pystac.Provider(name=coll_api['partners'], url='', description=""))

        provider = {
            "abbreviation": "",
            "contact": "",
            "data_website": "",
            "name": ""
        }
        if(coll_api["source_abbreviation"] or coll_api["source_contact"] or coll_api["source_data_website"] or coll_api["source_name"]):
            
            if(coll_api["source_abbreviation"]):
                provider["abbreviation"] = coll_api['source_abbreviation']
            
            if(coll_api["source_contact"]):
                provider["contact"] = coll_api['source_contact']

            if(coll_api["source_data_website"]):
                provider["data_website"] = coll_api['source_data_website']

            if(coll_api["source_name"]):
                provider["name"] = coll_api['source_name']
            
            self.providers.append(pystac.Provider(name=provider["name"], url=provider["data_website"],
                extra_fields={
                    "data_website": provider["data_website"],
                    "contact": provider["contact"]
                }))

        # Configure some standard collection values.
        self.description = coll_api["description"]
        self.keywords = self.csv_to_arr(coll_api['tags'])
        self.extra_fields["title"] = coll_api["name"]

        if(coll_api["wms_link"]):
            wms_link = pystac.Asset(
                href=coll_api["wms_link"],
                media_type="text"
            )
            self.add_asset("wms_link", wms_link)

        if(coll_api["tile_index_url"]):
            tile_index_url = pystac.Asset(
                href=coll_api["tile_index_url"],
                media_type="text"
            )
            self.add_asset("tile_index_url", tile_index_url)
        
        if(coll_api["lidar_breaklines_url"]):
            lidar_breaklines_url = pystac.Asset(
                href=coll_api["lidar_breaklines_url"],
                media_type="text"
            )
            self.add_asset("lidar_breaklines_url", lidar_breaklines_url)

        if(coll_api["lidar_buildings_url"]):
            lidar_buildings_url = pystac.Asset(
                href=coll_api["lidar_buildings_url"],
                media_type="text"
            )
            self.add_asset("lidar_buildings_url", lidar_buildings_url)

        if(coll_api["supplemental_report_url"]):
            supplemental_report_url = pystac.Asset(
                href=coll_api["supplemental_report_url"],
                media_type="text"
            )
            self.add_asset("supplemental_report_url", supplemental_report_url)

        self.resolution = coll_api['resolution']



        # Configure creation time.
        try:
            self.created = datetime.strptime(coll_api['acquisition_date'], "%Y-%m-%d")
        except Exception as e:
            log_exception(f"Could not calculate timestamp while setting metadata for {coll_api['name']}")

    def get_tile_index_collectionwide_data(self, index_path: str):
        """
        Implement a build of a stac item using tile index. Required by Joey.

        Joey's requirements below.
        Tile extent for 3d data.
        Always use Tile index geometry if it exists, only fall back to lpc or hypso if there is no tile index data.
        This will be reflected in stac as well.
        :param self: Description
        :param rsc: Description
        :type rsc: Resource
        :return: Description
        :rtype: Item
        """
        try:
            vsi_path = ""
            if(".tif" in index_path):
                raster_file = f"/vsicurl/{self.wh_client.get_filename_path(index_path)}"
                gdal_path = gdal.Open(raster_file)
                geom = json.loads("""
                {
                    "type": "FeatureCollection",
                    "features": [
                                                        {
                                "type": "Feature",
                                "geometry": {
                                    "type": "Point",
                                    "coordinates": [102.0, 0.5]
                                }
                            }]}""")
 
                tile_index = {}
                tile_index['dict'] = gdal_path.GetMetadata_Dict()
                tile_index['convex_hull_polygon'] = geom

                return tile_index
            else:
                vsi_path = f"/vsizip/vsicurl/{self.wh_client.get_filename_path(index_path)}"
                self.panda_layer = gpd.GeoDataFrame.from_file(vsi_path).to_crs("EPSG:4326")
                self.tile = self.panda_layer.to_dict()
                union = self.panda_layer.union_all()
                tile_index = {}
                tile_index['dict'] = self.panda_layer.to_dict()
                tile_index['convex_hull_polygon'] = json.loads(shapely.to_geojson(union.convex_hull))

                return tile_index
        except Exception as e:
            log_exception(e)
            return None

    def build_stac_items(self):
        resources = []
        whc: DataFrame = DataFrame(data=self.s3_collection.paths.ITEMS)
        processes = []
        GC_INTERVAL = 500 # Frequency at which this program will run garbage collection while building items.

        # count = 0
        for wh in whc.itertuples():
            # count = count+1
            # if count > GC_INTERVAL:
            #     print("Running garbage collector.")
            #     gc.collect()
            #     count = 0
            #     print("Garbage collection done.")
            item = wh[1]
            i = wh[0]
            next_index=None
            if(i+1 < len(whc.values)):
                next_index = whc.values[i+1][0].index
            resources.append(item)
            title = f"{self.root}-{item.ext.split('.')[-1]}"
            if item.ext == '.aux':
                asset_item = pystac.ItemAssetDefinition({
                    "description": "Metadata in aux format.",
                    "ext": item.ext,
                    "media_type": "text/x-stex",
                    "roles": [item.type, "metadata", item.ext],
                    "title": title
                })

                self.item_assets[title] = asset_item
            elif item.ext == '.sdw':
                asset_item = pystac.ItemAssetDefinition({
                    "description": "Metadata in sdw format.",
                    "ext": item.ext,
                    "media_type": "application/vnd.stardivision.writer",
                    "roles": [item.type, "metadata", item.ext],
                    "title": title
                })

                self.item_assets[title] = asset_item
            elif item.ext == '.sid':
                    asset_item = pystac.ItemAssetDefinition({
                        "description": "Data in sid format.",
                        "ext": item.ext,
                        "media_type": "image/x-mrsid",
                        "roles": [item.type, "data", item.ext],
                        "title": title
                    })

                    self.item_assets[title] = asset_item
            elif item.ext.endswith(".xml"):
                    asset_item = pystac.ItemAssetDefinition({
                        "description": "Metadata in xml format.",
                        "ext": item.ext,
                        "media_type": "application/xml",
                        "roles": [item.type, "metadata", item.ext],
                        "title": title
                    })

                    self.item_assets[title] = asset_item
            elif item.ext.endswith(".zip"):
                    asset_item = pystac.ItemAssetDefinition({
                        "description": "Zip archive.",
                        "ext": item.ext,
                        "media_type": "application/zip",
                        "roles": [item.type, "data", item.ext],
                        "title": title
                    })

                    self.item_assets[title] = asset_item
            elif item.ext.endswith(".tif"):
                    asset_item = pystac.ItemAssetDefinition({
                        "description": "Tif image.",
                        "ext": item.ext,
                        "media_type": "image/tiff",
                        "roles": [item.type, "data", item.ext],
                        "title": title
                    })

                    self.item_assets[title] = asset_item
            elif item.ext.endswith(".laz"):
                    asset_item = pystac.ItemAssetDefinition({
                        "description": "Zipped Lidar.",
                        "ext": item.ext,
                        "media_type": "application/vnd.las",
                        "roles": [item.type, "data", item.ext],
                        "title": title
                    })

                    self.item_assets[title] = asset_item
            elif item.ext.endswith(".img"):
                    asset_item = pystac.ItemAssetDefinition({
                        "description": "Raster Image file.",
                        "ext": item.ext,
                        "media_type": "image/x-img",
                        "roles": [item.type, "data", item.ext],
                        "title": title
                    })

                    self.item_assets[title] = asset_item
            elif item.ext.endswith(".jp2"):
                    asset_item = pystac.ItemAssetDefinition({
                        "description": "Raster Image file.",
                        "ext": item.ext,
                        "media_type": "image/jp2",
                        "roles": [item.type, "data", item.ext],
                        "title": title
                    })

                    self.item_assets[title] = asset_item
            elif item.ext.endswith(".txt"):
                    asset_item = pystac.ItemAssetDefinition({
                        "description": "Text File.",
                        "ext": item.ext,
                        "media_type": "text/plain",
                        "roles": [item.type, "metadata", item.ext],
                        "title": title
                    })

                    self.item_assets[title] = asset_item
            elif item.ext.endswith(".j2w"):
                    asset_item = pystac.ItemAssetDefinition({
                        "description": "Image File.",
                        "ext": item.ext,
                        "media_type": "application/octet-stream",
                        "roles": [item.type, "metadata", item.ext],
                        "title": title
                    })

                    self.item_assets[title] = asset_item
            else:
                print(f"Filetype {item.ext} not found for stac_items in: {self.root}")

            # tx_collection.item_assets.update()
            if(item.index == next_index):
                #Proceed to add the next item to the resources array to combine into one item.
                continue
            # self.add_stac_items(resources, self.root, COMPLETE_REBUILD_FLAG)
            self.add_stac_items(resources, self.root, COMPLETE_REBUILD_FLAG)
            resources = []

        # pool = Pool(len(processes))
        # pool.map(self.add_stac_items, processes)
        # pool.join()
        #print("Hi")