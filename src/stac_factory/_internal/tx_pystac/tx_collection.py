import json, pystac, geopandas, os
from osgeo import gdal
from pandas import DataFrame
from pathlib import Path

# Local imports
from stac_factory.root import CITY_BOUNDARIES, COUNTY_BOUNDARIES, TEST_GEOJSON_ROOT

from .tx_item import TxItem
from .file_parsing import file_types, RoleBuilder
from .tx_types import TileIndex

# AWS Imports
from .. import S3Collection, WarehouseClient, S3Config
from ..util import log_info, log_exception

BUILD_TEST_GEOJSON = False

gdal.UseExceptions()


class CollectionException(Exception):
    pass


class TxCollection(pystac.Collection):
    extra_fields = {}
    settings = {"LAZ_3D_BBOX": True, "API_URL": "https://api.tnris.org"}
    panda_layer: geopandas.GeoDataFrame
    resolution: str
    s3_collection: S3Collection
    wh_client: WarehouseClient
    data_wh_configuration: S3Config
    index: TileIndex
    href: str
    assets: dict

    def __init__(
        self,
        data_wh_configuration: S3Config,
        s3_collection,
        collection_name,
        stac_extensions,
        textent: pystac.TemporalExtent,
        description="",
        is_s3=True
    ):
        href = f"./catalog/{collection_name}/collection.json"
        wh_client: WarehouseClient = WarehouseClient(data_wh_configuration)
        # Configure panda_layer using geopandas, vsipathing capabilities.
        vsi_path = f"/vsizip/vsicurl/{wh_client.get_filename_path(s3_collection.index_asset.path)}"
        panda_layer = None
        if(is_s3):
            panda_layer = geopandas.GeoDataFrame.from_file(vsi_path, layer=0).to_crs(
                "EPSG:4326"
            )
        else:
            panda_layer = geopandas.GeoDataFrame.from_file(s3_collection.index_asset.path, layer=0).to_crs(
                "EPSG:4326"
            )
        spatial_extent = pystac.SpatialExtent(panda_layer.total_bounds.tolist())
        extent = pystac.Extent(spatial_extent, textent)
        super().__init__(
            id=collection_name,
            description=description,
            stac_extensions=stac_extensions,
            href=href,
            extent=extent,
            catalog_type=pystac.CatalogType.SELF_CONTAINED,
        )
        self.is_s3 = is_s3
        self.panda_layer = panda_layer

        self.wh_client: WarehouseClient = wh_client
        self.data_wh_configuration = data_wh_configuration
        self.s3_collection = s3_collection
        self.collection_name = collection_name
        self.stac_extensions = stac_extensions

        self.tile = self.panda_layer.to_dict()
        self.index: TileIndex = TileIndex(self.panda_layer)

        # if ('VerDate' in self.index.dict):
        #     temporal = pystac.TemporalExtent([datetime.fromisoformat(self.index.dict.get("VerDate")), datetime.fromisoformat(self.index.dict.get("VerDate"))])

        self.construct_spatial_tags()
        if self.index:
            self.extra_fields["txgio:geometry"] = self.index.outline

        self.builder = RoleBuilder(data_wh_configuration.BUCKET_URL)

    def construct_spatial_tags(self):
        # Tag counties
        counties = geopandas.read_file(COUNTY_BOUNDARIES)
        counties_buffer = open(COUNTY_BOUNDARIES)
        counties_dict = json.load(counties_buffer)
        intersections = counties.intersects(self.index.simplify)
        spatial_tags = ""

        for i in range(len(intersections)):
            if intersections[i]:
                spatial_tags += (
                    f",{counties_dict['features'][i]['properties']['CNTY_NM']}"
                )

        # Tag cities
        cities = geopandas.read_file(COUNTY_BOUNDARIES)
        cities_buffer = open(CITY_BOUNDARIES)
        cities_dict = json.load(cities_buffer)
        intersections2 = cities.intersects(self.index.simplify)
        for i in range(len(intersections2)):
            if intersections2[i]:
                spatial_tags += f",{cities_dict['objects']['TX_Cities']['geometries'][i]['properties']['name']}"
        try:
            if BUILD_TEST_GEOJSON:
                path = f"{TEST_GEOJSON_ROOT}/{self.stac_id.split('_')[0]}/items"
                if not os.path.exists(path):
                    os.makedirs(path)
                with open(
                    f"{TEST_GEOJSON_ROOT}/{self.collection_name}_testgeom.geojson", "w"
                ) as f:
                    f.write(self.index.outline)
        except:
            log_info("Couldn't write an example geojson")

        self.extra_fields["txgio:spatial_keywords"] = spatial_tags[1:]

    def csv_to_arr(self, csv: str) -> list[str]:
        if not csv or len(csv) < 1:
            return []

        vals = csv.split(",")
        for val in enumerate(vals):
            vals[val[0] - 1] = vals[val[0] - 1].strip()
        return vals

    def add_stac_items(self, resources) -> pystac.Item | pystac.STACObject | None:
        """
        Create, validate, and add a STAC item for a group of resources.

        Args:
            resources: Resources used to construct the STAC item.

        Returns:
            The created STAC item if successful; otherwise None.

        Notes:
            The item is validated before being added to the collection. If
            item creation or validation fails, the exception is logged and
            None is returned.
        """

        tx_item = None
        sreference: str | list[str] | None = self.extra_fields.get(
            "txgio:spatial_reference"
        )

        try:
            tx_item = TxItem(
                resources,
                sreference,
                self.id,
                self.tile,
                self.resolution,
                self.data_wh_configuration,
                self.builder,
            )
            tx_item.validate()
        except Exception as e:
            log_exception(e)
            return None

        if tx_item and len(resources) and len(tx_item.links):
            self.add_item(item=tx_item)
            return tx_item
        else:
            log_info(f"No known filetype for filename: {resources[0].filename}.")
            return None

    def build_stac_items(self):
        resources = []
        whc: DataFrame = DataFrame(data=self.s3_collection.paths.ITEMS)
        builder = RoleBuilder(self.data_wh_configuration.BUCKET_URL)

        def build_asset_item(item, description, media_type):
            title = f"{self.collection_name}-{item.ext.split('.')[-1]}"
            if self.item_assets.get(title):
                return  # No need to continue it already exists.

            if item.ext == ".zip":
                title = f"{title}-{item.type}"

            roles = builder.build_roles_for(item, uniform_zip=True)

            asset_item = pystac.ItemAssetDefinition(
                {
                    "description": description,
                    "ext": item.ext,
                    "media_type": media_type,
                    "roles": roles,
                    "title": title,
                }
            )
            self.item_assets[title] = asset_item

        for wh in whc.itertuples():
            item = wh[1]
            i = wh[0]
            next_index = None
            if i + 1 < len(whc.values):
                next_index = whc.values[i + 1][0].index
            if(not self.is_s3):
                item.path = Path(item.path).relative_to("/").as_posix()
            resources.append(item)
            type = file_types[item.ext]
            build_asset_item(item, type.get("description"), type.get("media_type"))

            # tx_collection.item_assets.update()
            if item.index == next_index:
                # Proceed to add the next item to the resources array to combine into one item.
                continue
            self.add_stac_items(resources)
            resources = []
