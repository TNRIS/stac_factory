import pystac, shapely, json, pdal, remotezip, os
from datetime import datetime
from osgeo import gdal
from shapely.geometry import mapping
from typing import List, assert_type
import geopandas as gpd

from root import TEST_GEOJSON_ROOT
from .tx_asset import TxAsset
from .file_parsing import build_roles_for
from extensions.tx_aws.s_three import WarehouseClient, Resource
from src.stac_util import log_info, log_exception, stream_handler


class ItemException(Exception):
    pass


class TxItem(pystac.Item):
    """
    Docstring for TxItem
    Override pystacs Item
    """

    def __init__(
        self,
        resources: List[Resource],
        spatial_reference: str | list[str] | None,
        collection_name: str,
        preprocessed_geometry: dict | None,
        resolution: str | None,
        data_wh_configuration,
    ):
        """
        TxItem Constructor

        :param self: self
        :param resource: aws resource
        :type resources: List[Resource]
        :param spatial_reference: Description
        :param collection_name: Description
        """
        if isinstance(spatial_reference, list):
            spatial_reference = spatial_reference[0]
        elif not spatial_reference:
            spatial_reference = "EPSG:4326"
        self.spatial_reference = spatial_reference
        self.wh_client: WarehouseClient = WarehouseClient(data_wh_configuration)
        self.stac_id = f"{collection_name}_{resources[0].index}"
        self.kwargs = gdal.InfoOptions(allMetadata=True, format="json", stats=True)
        assets: dict[str, pystac.Asset] = {}
        # resource.type, f"/{resource.path}", resource.filename

        geometries = None

        tile_id = None
        try:
            tile_id = resources[0].index
        except Exception as e:
            log_info(f"Cannot find tile_id for resource {collection_name}")
        if preprocessed_geometry and tile_id and len(tile_id):
            tile_name_map = {}

            # Workaround Tile ID names. Going forward this will be more consistently named. But the initial migration will have many different names here.
            if "TileID" in preprocessed_geometry:
                tile_name_map = preprocessed_geometry["TileID"].items()
            elif "CNTY_FIPS" in preprocessed_geometry:
                tile_name_map = preprocessed_geometry["CNTY_FIPS"].items()
            elif "STATE_FIPS" in preprocessed_geometry:
                tile_name_map = preprocessed_geometry["STATE_FIPS"].items()
            elif "FlightDate" in preprocessed_geometry:
                tile_name_map = preprocessed_geometry["FlightDate"].items()

            if tile_name_map == {}:
                log_info("Can't find a tile id")
            index = None
            for key, val in tile_name_map:
                if str(val) == tile_id:
                    index = key

            if index == None:  # 0 is a valid index so check for None specifically.
                raise Exception(
                    f"No index for TxItem with tile_id: {tile_id} in {self.stac_id}"
                )
            geometries = []
            s_geom = preprocessed_geometry["geometry"][index]
            simplify = s_geom.simplify(
                tolerance=0.0001, preserve_topology=True
            )  # Defaults to Douglas Peucker, recommended in api for the_geom.
            geometries.append(simplify)
            TEST_EXPORT_ITEM = False # Change this to True if you want to have geojson to test with.
            if( TEST_EXPORT_ITEM):
                try:
                    path = f"{TEST_GEOJSON_ROOT}/{self.stac_id.split('_')[0]}/items"
                    if not os.path.exists(path):
                        os.makedirs(path)
                    with open(f"{path}/{self.stac_id}_testgeom.geojson", "w") as f:
                        f.write(shapely.to_geojson(simplify))
                except:
                    log_info("Can't write a test file skipping.")
            geometries.append(preprocessed_geometry["geometry"][index].bounds)
        else:
            geometries = self.get_geom_by_priority(resources)

        for resource in resources:
            if resource.index == tile_id:
                roles = build_roles_for(resource)

                asset = TxAsset(
                    resource,
                    collection_name,
                    resolution,
                    roles=roles,
                    extra_fields={
                        "file:size": resource.size,
                        "file:local_path": resource.path,
                    },
                )
                # if not hasattr(asset,"set_owner"):
                #     asset.set_owner = pystac.Asset.set_owner
                # asset.set_owner = pystac.Asset.set_owner
                assets[f"{collection_name}-{resource.ext.split(".")[-1]}"] = asset
            # extra_fields={
            #         "file:checksum":resource.etag.split("\"")[1],
            #         "file:size":resource.size,
            #         "file:local_path":resource.path
            #     }
            # assets[resource.fname]["file:checksum"]=resource.etag.split("\"")[1]
            # assets[resource.fname]["file:size"]=resource.size,
            # assets[resource.fname]["file:local_path"]=resource.path

        geometry = geometries[0]
        bbox = geometries[1]
        super(TxItem, self).__init__(
            id=self.stac_id,
            geometry=mapping(geometry),
            bbox=list(bbox),
            datetime=datetime.utcnow(),
            properties={},
            stac_extensions=[
                "https://stac-extensions.github.io/file/v2.1.0/schema.json"
            ],
            href=f"catalog/{collection_name}/{self.stac_id}.json",
            assets=assets,
        )

        return

    def get_geom_by_priority(self, resources: List[Resource]):
        """
        Get a geometry. Currently prioritizing tile_index if available then speed.

        :param self: Description
        :param resources: Description
        :type resources: List[Resource]
        :return: Description
        :rtype: str
        """
        geom = ""

        def rsc_contains(type: str):
            # return any(x.type == type for x in resources)
            for resource in resources:
                if resource.type == type:
                    return resource
                else:
                    return None

        dem_item = rsc_contains("dem")
        if dem_item:
            return self.build_dem_stac(dem_item)

        lpc_item = rsc_contains("lpc")
        if lpc_item:
            return self.build_laz_stac(lpc_item)

        hypso_item = rsc_contains("hypso")
        if hypso_item:
            return self.build_shp_stac(hypso_item)

        cir_item = rsc_contains("cir") or rsc_contains("nccir")
        if cir_item:
            return self.build_cir_stac(cir_item)

        address_points_item = rsc_contains("address-points")
        if address_points_item:
            if address_points_item.filename.endswith("fgdb"):
                return self.build_fgdb_stac(address_points_item)
            elif address_points_item.filename.endswith("shp"):
                return self.build_shp_stac(address_points_item)

        shp_item = rsc_contains("shp")
        if shp_item:
            return self.build_shp_stac(shp_item)

    def get_file(self, rsc: Resource):
        try:
            return remotezip.RemoteZip(
                self.wh_client.get_filename_path(rsc.path)
            ).filelist
        except Exception as e:
            log_info(
                f"{self.wh_client.get_filename_path(rsc.path)} cannot be unzipped. Proceeding to next item without making a stac resource."
            )
            return None

    def build_dem_stac(self, rsc: Resource):
        """ """
        zip_files = self.get_file(rsc)

        if not zip_files:
            return zip_files

        ginfo = None

        for file in zip_files:
            if file.filename.endswith(".img"):
                vsi_path = f"/vsizip/vsicurl/{self.wh_client.get_filename_path(rsc.path)}/{file.filename}"
                ginfo = gdal.Info(vsi_path, options=self.kwargs)

                return [
                    ginfo["wgs84Extent"],
                    pystac.utils.geometry_to_bbox(ginfo["wgs84Extent"]),
                ]

    def build_shp_stac(self, rsc: Resource):
        """
        Get shp data use ogr

        :param self: Description
        :param rsc_path: Description
        :type rsc_path: str
        :param resource_zip: Description
        :type resource_zip: str
        :param rsc_ext: Description
        :type rsc_ext: str
        :param coll_api: Description
        :type coll_api: dict
        """

        # Open Dataset and get Vector information
        vsi_path = f"/vsizip/vsicurl/{self.wh_client.get_filename_path(rsc.path)}"
        try:
            panda_layer = gpd.GeoDataFrame.from_file(vsi_path).to_crs("EPSG:4326")
            union = panda_layer.union_all()
            outline = json.loads(shapely.to_geojson(union.convex_hull))

            return [outline, panda_layer.total_bounds.tolist()]
        except Exception as e:
            log_info(f"Can't find the file: {vsi_path}")
            return None

    def build_gdb_stac(self, rsc: Resource):
        zip_files = self.get_file(rsc)
        if not zip_files:
            return zip_files

        ginfo = None
        for file in zip_files:
            if file.filename.endswith(".gdb"):
                vsi_path = f"/vsizip/vsicurl/{self.wh_client.get_filename_path(rsc.path)}/{file.filename}"
                ginfo = gdal.Info(vsi_path, options=self.kwargs)

        if ginfo:
            return [
                ginfo["wgs84Extent"],
                pystac.utils.geometry_to_bbox(ginfo["wgs84Extent"]),
            ]
        else:
            return None

    def build_fgdb_stac(self, rsc: Resource):
        zip_files = self.get_file(rsc)

        if not zip_files:
            return zip_files

        gdb_name = zip_files[0].filename
        loc = self.wh_client.get_filename_path(rsc.path)
        panda_layer = gpd.GeoDataFrame.from_file(f"/vsizip/vsicurl/{loc}/{gdb_name}")
        union = panda_layer.union_all()
        outline = json.loads(shapely.to_geojson(union.convex_hull))

        return [outline, panda_layer.total_bounds.tolist()]

    def build_laz_stac(self, rsc: Resource):
        """
        The meta name simply follows the zip name with .met.
        """
        vsi_path = f"/vsizip/vsicurl/{self.wh_client.get_filename_path(rsc.path)}"
        files = gdal.ReadDir(vsi_path)

        if files and len(files) > 1:
            vsi_path = (
                f"{vsi_path}/{[file for file in files if file.endswith('.laz')][0]}"
            )

        pipeline = (
            pdal.Reader.las(
                filename=vsi_path, default_srs=f"EPSG:{self.spatial_reference}"
            )
            | pdal.Filter.stats()
        )
        pipeline.execute()
        stats = pipeline.metadata.get("metadata").get("filters.stats")
        bounds = stats.get("bbox").get("EPSG:4326").get("outline")
        bbox = pipeline.metadata["metadata"]["filters.stats"]["bbox"][f"EPSG:4326"][
            "bbox"
        ]
        bbox = [bbox["maxx"], bbox["maxy"], bbox["minx"], bbox["miny"]]

        return [bounds, bbox]

    def build_cir_stac(self, rsc: Resource):
        """
        Docstring for build_cir_stac

        :param self: Description
        :param rsc: Description
        :type rsc: Resource
        :return: Description
        :rtype: Item
        """
        bbox = [0, 0, 0, 0]
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

        return [geom, bbox]
