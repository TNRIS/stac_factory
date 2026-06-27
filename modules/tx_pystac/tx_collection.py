import json, pystac, geopandas
from typing import List
from modules.tx_aws.aws_types import S3Config
from osgeo import gdal
from pandas import DataFrame

from root import ROOT

from .tx_item import TxItem
from .file_parsing import file_types, build_roles_for
from .tx_types import TileIndex

from modules.tx_aws.s_three import Collection as S3Collection, WarehouseClient, Resource
from stac_factory.stac_util import log_info, log_exception

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
        data_wh_configuration,
        s3_collection,
        collection_name,
        stac_extensions,
        textent: pystac.TemporalExtent,
        description="",
    ):
        href = f"./catalog/{collection_name}/collection.json"
        wh_client: WarehouseClient = WarehouseClient(data_wh_configuration)
        # Configure panda_layer using geopandas, vsipathing capabilities.
        vsi_path = f"/vsizip/vsicurl/{wh_client.get_filename_path(s3_collection.index_asset[0].path)}"
        panda_layer = geopandas.GeoDataFrame.from_file(vsi_path, layer=0).to_crs(
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

    def construct_spatial_tags(self):
        # Tag counties
        counties = geopandas.read_file(
            f"{ROOT}/txgio_extension/county_boundaries.geojson"
        )
        counties_buffer = open(f"{ROOT}/txgio_extension/county_boundaries.geojson")
        counties_dict = json.load(counties_buffer)
        intersections = counties.intersects(self.index.simplify)
        spatial_tags = ""

        for i in range(len(intersections)):
            if intersections[i]:
                spatial_tags += (
                    f",{counties_dict['features'][i]['properties']['CNTY_NM']}"
                )

        # Tag cities
        cities = geopandas.read_file(
            ROOT / "txgio_extension" / "county_boundaries.geojson"
        )
        cities_buffer = open(ROOT / "txgio_extension" / "TX_Cities.json")
        cities_dict = json.load(cities_buffer)
        intersections2 = cities.intersects(self.index.simplify)
        for i in range(len(intersections2)):
            if intersections2[i]:
                spatial_tags += f",{cities_dict['objects']['TX_Cities']['geometries'][i]['properties']['name']}"
        try:
            if BUILD_TEST_GEOJSON:
                with open(
                    f"{ROOT}/testgeojson/{self.collection_name}_testgeom.geojson", "w"
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

    def add_stac_items(
        self, resources: List[Resource]
    ) -> pystac.Item | pystac.STACObject | None:
        """
        Docstring for add_stac_items

        :param self: Description
        :param resources: Description
        :type resources: List[Resource]
        :return: Description
        :rtype: Item | STACObject | None
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

        def build_asset_item(item, description, media_type):
            title = f"{self.collection_name}-{item.ext.split('.')[-1]}"

            if item.ext == ".zip":
                title = f"{title}-{item.type}"

            roles = build_roles_for(resource=item)

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
            resources.append(item)
            type = file_types[item.ext]
            build_asset_item(item, type.get("description"), type.get("media_type"))

            # tx_collection.item_assets.update()
            if item.index == next_index:
                # Proceed to add the next item to the resources array to combine into one item.
                continue
            self.add_stac_items(resources)
            resources = []
