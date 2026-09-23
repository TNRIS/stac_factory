import pystac, requests
from datetime import datetime
import pandas

from stac_factory.root import ROOT, CROSS_WALK
from .tx_collection import TxCollection

# AWS imports
from .. import S3Collection, S3Config
from ..util import log_info, log_exception


class TxHistoricCollection(TxCollection):
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
            coll_api = self.lore_xwalk(collection_name)

            if not s3_collection.index_asset:
                log_info(f"{collection_name} has no index asset.")
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

    def lore_xwalk(self, name):
        coll_api_url = ""

        try:
            coll_api_url = f'{self.settings["API_URL"]}/api/v1/historical/collections?collection_id={name}'
            return requests.get(coll_api_url).json()
        except Exception as e:
            print(e)

        cross_walk = pandas.read_excel(CROSS_WALK, ["LORE"])["LORE"]
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
            elif category in ["Historic_Imagery"]:
                categories[i] = "Historic Imagery"
        categories = list(
            set(categories)
        )  # Convert to a set, then back to list to remove duplicates

        self.extra_fields["txgio:categories"] = categories
        self.extra_fields["txgio:collection_id"] = coll_api["collection_id"]
        self.extra_fields["txgio:publication_date"] = coll_api["acquisition_date"]
        self.extra_fields["txgio:spatial_reference"] = []
        self.extra_fields["txgio:citation"] = "PLACEHOLDER"
        self.extra_fields["txgio:s_three_bucket_key"] = self.collection_name
        self.extra_fields["txgio:public"] = coll_api["public"]
        self.extra_fields["txgio:availability"] = coll_api["availability"] == "Download"
        self.extra_fields["txgio:banner_text"] = "PLACEHOLDER"
        self.extra_fields["txgio:last_modified"] = str(datetime.today())
        self.extra_fields["txgio:last_edited_by"] = "Initial create"
        self.extra_fields["txgio:template"] = coll_api["template"]

        # Historic-specific fields
        self.extra_fields["txgio:fully_scanned"] = coll_api["fully_scanned"]
        self.extra_fields["txgio:photo_index_only"] = coll_api["photo_index_only"]
        self.extra_fields["txgio:media_type"] = coll_api["media_type"]
        self.extra_fields["txgio:general_scale"] = coll_api["general_scale"]
        self.extra_fields["txgio:products"] = coll_api["products"]

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


        # Historic service assets
        if coll_api["index_service_url"]:
            self.add_asset(
                "index_service_url",
                pystac.Asset(
                    href=coll_api["index_service_url"],
                    media_type="text",
                ),
            )

        if coll_api["frames_service_url"]:
            self.add_asset(
                "frames_service_url",
                pystac.Asset(
                    href=coll_api["frames_service_url"],
                    media_type="text"
                )
            )

        if coll_api["mosaic_service_url"]:
            self.add_asset(
                "mosaic_service_url",
                pystac.Asset(
                    href=coll_api["mosaic_service_url"],
                    media_type="text"
                )
            )

        if coll_api["scanned_index_ls4_links"]:
            scanned_index_ls4_links = pystac.Asset(
                href=coll_api["scanned_index_ls4_links"], media_type="text"
            )
            self.add_asset("scanned_index_ls4_links", scanned_index_ls4_links)


        source = {
            "name": "",
            "abbreviation": None,
            "website": None,
            "data_website": None,
            "contact": None
        }

        if (
            coll_api["source_abbreviation"]
            or coll_api["source_contact"]
            or coll_api["source_data_website"]
            or coll_api["source_name"]
        ):

            if coll_api.get("source_abbreviation"):
                source["abbreviation"] = coll_api["source_abbreviation"]

            if coll_api.get("source_contact"):
                source["contact"] = coll_api["source_contact"]

            if coll_api.get("source_data_website"):
                source["data_website"] = coll_api["source_data_website"]

            if coll_api.get("source_website"):
                source["website"] = coll_api["source_website"]

            if coll_api.get("source_name"):
                source["name"] = coll_api["source_name"]

        self.extra_fields["txgio:source"] = source
        # Configure some standard collection values.
        self.description = coll_api["about"]
        self.extra_fields["title"] = coll_api["name"]

        # Configure creation time.
        try:
            self.created = datetime.strptime(coll_api["acquisition_date"], "%Y-%m-%d")
        except Exception as e:
            log_exception(
                f"Could not calculate timestamp while setting metadata for {coll_api['name']}"
            )
