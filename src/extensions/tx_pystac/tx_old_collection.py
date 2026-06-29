import pystac, requests
from datetime import datetime
import pandas

from .tx_collection import TxCollection
from root import ROOT, CROSS_WALK
from extensions.tx_aws import Collection as S3Collection
from extensions.tx_aws.aws_types import S3Config
from src.stac_util import log_info, log_exception


class TxOldCollection(TxCollection):
    collection_name: str
    stac_extensions: list[str]

    def __init__(
        self,
        collection_name: str,
        s3_collection: S3Collection,
        data_wh_configuration: S3Config,
        stac_extensions: list[str] = [
            "https://test-gio-data-warehouse.s3.us-east-1.amazonaws.com/spec/schema.json",
            "https://stac-extensions.github.io/file/v2.1.0/schema.json",
        ],
    ):

        try:
            # Run the cross walk function.
            coll_api = self.lcd_xwalk(collection_name)

            if not len(s3_collection.index_asset):
                print(f"{collection_name} index asset is empty")
                return

            # Default extents. (Required for constructor)
            if coll_api:
                temporal: pystac.TemporalExtent = pystac.TemporalExtent(
                    [
                        datetime.fromisoformat("0001-01-01"),
                        datetime.fromisoformat("0001-01-01"),
                    ]
                )
                coll_api = coll_api["results"][0]

                if "acquisition_date" in coll_api:
                    temporal = pystac.TemporalExtent(
                        [
                            datetime.fromisoformat(coll_api.get("acquisition_date")),
                            datetime.fromisoformat(coll_api.get("acquisition_date")),
                        ]
                    )
                else:
                    log_info(f"No temporal extent available for {collection_name}")

                description = coll_api.get("description")
                if not description:
                    description = coll_api.get("about")

                super().__init__(
                    data_wh_configuration=data_wh_configuration,
                    s3_collection=s3_collection,
                    collection_name=collection_name,
                    stac_extensions=stac_extensions,
                    textent=temporal,
                    description=description,
                )
                self.__set_collection_meta_data(coll_api)
                self.build_stac_items()
            else:
                log_info(f"There is no api entry found for {collection_name}")

        except Exception as e:
            log_info(f"Cannot build metadata from api. {collection_name}")
            log_exception(e)
            return None

    def lcd_xwalk(self, name):
        coll_api_url = (
            f'{self.settings["API_URL"]}/api/v1/collections?s_three_key={name}'
        )
        coll_api = requests.get(coll_api_url).json()

        if len(coll_api["results"]):
            return coll_api
        else:
            cross_walk = pandas.read_excel(
                CROSS_WALK
                ["LCD"],
            )["LCD"]

            for i in cross_walk.itertuples():

                if i._5 == name or i._4 == name:
                    coll_api_url = f'{self.settings["API_URL"]}/api/v1/collections?collection_id={i[3]}'
                    coll_api = requests.get(coll_api_url).json()
                    if len(coll_api["results"]):
                        return coll_api
                    else:
                        log_info(f"Cannot find api results for {coll_api_url}")

    def lore_xwalk(self, name):
        coll_api_url = ""
        coll_api = ""

        try:
            coll_api_url = f'{self.settings["API_URL"]}/api/v1/historical/collections?collection_id={name}'
            return requests.get(coll_api_url).json()
        except Exception as e:
            print(e)

        cross_walk = pandas.read_excel(
            CROSS_WALK, ["LORE"]
        )["LORE"]
        for i in cross_walk.itertuples():
            if i[8] == name:
                coll_api_url = f'{self.settings["API_URL"]}/api/v1/historical/collections?collection_id={i.collection_id}'
                return requests.get(coll_api_url).json()

    def __set_collection_meta_data(self, coll_api: dict):
        """
        Docstring for set_collection_meta_data

        :param self: Stac Builder
        """
        categories = self.csv_to_arr(coll_api["category"])

        for i, category in enumerate(categories):
            if category in ["Lidar", "Bathymetry"]:
                categories[i] = "Elevation"
            elif category in ["Land_Cover"]:
                categories[i] = "Basemap"
        categories = list(
            set(categories)
        )  # Convert to a set, then back to list to remove duplicates

        self.extra_fields["txgio:categories"] = categories
        self.extra_fields["txgio:collection_id"] = coll_api["collection_id"]
        self.extra_fields["txgio:publication_date"] = coll_api["publication_date"]
        self.extra_fields["txgio:notes"] = (
            coll_api["known_issues"] or ""
        )  # Use remarks in historic collections.
        self.extra_fields["txgio:spatial_reference"] = self.csv_to_arr(
            coll_api["spatial_reference"]
        )
        self.extra_fields["txgio:resolution"] = coll_api["resolution"]
        self.extra_fields["txgio:bands"] = self.csv_to_arr(coll_api["band_types"])
        self.extra_fields["txgio:citation"] = "PLACEHOLDER"
        self.extra_fields["txgio:s_three_bucket_key"] = self.collection_name
        self.extra_fields["txgio:public"] = coll_api["public"]
        self.extra_fields["txgio:availability"] = coll_api["availability"] == "Download"
        self.extra_fields["txgio:banner_text"] = "PLACEHOLDER"
        self.extra_fields["txgio:last_modified"] = str(datetime.today())
        self.extra_fields["txgio:last_edited_by"] = "Initial create"
        self.extra_fields["txgio:template"] = coll_api["template"]
        self.license = coll_api["license_abbreviation"]
        self.license = (
            coll_api["license_abbreviation"]
            if coll_api["license_abbreviation"]
            else "other"
        )

        if coll_api["thumbnail_image"]:
            thumbnail_image = pystac.Asset(
                href=coll_api["thumbnail_image"], media_type="text"
            )
            self.add_asset("thumbnail_image", thumbnail_image)

        if coll_api["images"]:
            images = pystac.Asset(href=coll_api["images"], media_type="text")
            self.add_asset("images", images)

        # Convert csv and category into a array. I chose to do it this way because it captures csv's with a space, and without.
        # Setup providers
        txGIO = pystac.Provider(
            name="TxGIO",
            url="https://geographic.texas.gov/",
            description="Texas Geographic Information Office",
        )
        self.providers = [txGIO]
        if coll_api["partners"] and (
            not (coll_api["partners"] == "Texas Water Development Board/TxGIO")
        ):
            self.providers.append(
                pystac.Provider(name=coll_api["partners"], url="", description="")
            )

        provider = {"abbreviation": "", "contact": "", "data_website": "", "name": ""}
        if (
            coll_api["source_abbreviation"]
            or coll_api["source_contact"]
            or coll_api["source_data_website"]
            or coll_api["source_name"]
        ):

            if coll_api["source_abbreviation"]:
                provider["abbreviation"] = coll_api["source_abbreviation"]

            if coll_api["source_contact"]:
                provider["contact"] = coll_api["source_contact"]

            if coll_api["source_data_website"]:
                provider["data_website"] = coll_api["source_data_website"]

            if coll_api["source_name"]:
                provider["name"] = coll_api["source_name"]

            self.providers.append(
                pystac.Provider(
                    name=provider["name"],
                    url=provider["data_website"],
                    extra_fields={
                        "data_website": provider["data_website"],
                        "contact": provider["contact"],
                    },
                )
            )

        # Configure some standard collection values.
        self.description = coll_api["description"]
        self.keywords = self.csv_to_arr(coll_api["tags"])
        self.extra_fields["title"] = coll_api["name"]

        if coll_api["wms_link"]:
            wms_link = pystac.Asset(href=coll_api["wms_link"], media_type="text")
            self.add_asset("wms_link", wms_link)

        if coll_api["tile_index_url"]:
            tile_index_url = pystac.Asset(
                href=coll_api["tile_index_url"], media_type="text"
            )
            self.add_asset("tile_index_url", tile_index_url)

        if coll_api["lidar_breaklines_url"]:
            lidar_breaklines_url = pystac.Asset(
                href=coll_api["lidar_breaklines_url"], media_type="text"
            )
            self.add_asset("lidar_breaklines_url", lidar_breaklines_url)

        if coll_api["lidar_buildings_url"]:
            lidar_buildings_url = pystac.Asset(
                href=coll_api["lidar_buildings_url"], media_type="text"
            )
            self.add_asset("lidar_buildings_url", lidar_buildings_url)

        if coll_api["supplemental_report_url"]:
            supplemental_report_url = pystac.Asset(
                href=coll_api["supplemental_report_url"], media_type="text"
            )
            self.add_asset("supplemental_report_url", supplemental_report_url)

        self.resolution = coll_api["resolution"]

        # Configure creation time.
        try:
            self.created = datetime.strptime(coll_api["acquisition_date"], "%Y-%m-%d")
        except Exception as e:
            log_exception(
                f"Could not calculate timestamp while setting metadata for {coll_api['name']}"
            )
