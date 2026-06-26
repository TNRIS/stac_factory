from .TxCollection import TxCollection
from app.aws.s_three import Collection as S3Collection
from app.stac import log_info, log_exception, stream_handler
import shapely, pdal, os, json, pystac, requests
from app.config.S3Config import S3Config
from app.aws.s_three import Collection as S3Collection
from datetime import datetime

class TxNewCollection(TxCollection):
    def __init__(self,
        whcollection: dict,
        s3_collection: S3Collection,
        data_wh_configuration,
        stac_extensions: list[str] = ["https://test-gio-data-warehouse.s3.us-east-1.amazonaws.com/spec/schema.json",
                                      "https://stac-extensions.github.io/file/v2.1.0/schema.json"]):
        iso_temporals = whcollection.get("extent").get("temporal").get("interval")
        temporals: list[list[datetime]] = []
        for temporal in iso_temporals:
            temporals.append([datetime.fromisoformat(temporal[0]), datetime.fromisoformat(temporal[1])])
            
        temporal = pystac.TemporalExtent(temporals)
        description = whcollection.get("description")

        super().__init__(data_wh_configuration, s3_collection, whcollection['id'], stac_extensions, temporal, description)

        self.whcollection = whcollection
        self.build_metadata_from_input()
        self.build_stac_items()
        return

    def build_metadata_from_input(self):
        self.s3_key = self.whcollection.get("id")
        self.extra_fields["txgio:s_three_bucket_key"] = self.s3_key #Remove later
        
        self.extra_fields["txgio:categories"]  = self.whcollection.get('txgio:categories')
        self.extra_fields["txgio:publication_date"] = self.whcollection.get("publication_date")
        if(self.whcollection.get("txgio:banner_text")):
            self.extra_fields["txgio:banner_text"] = self.whcollection.get("txgio:banner_text")

        if(self.whcollection.get("txgio:notes")):
            self.extra_fields["txgio:notes"] = self.whcollection.get("txgio:notes")
        if(self.whcollection.get("txgio:spatial_keywords")):
            self.extra_fields["txgio:spatial_keywords"] = self.whcollection.get("txgio:spatial_keywords")

        self.extra_fields["txgio:spatial_reference"] = self.whcollection.get("txgio:spatial_reference")
        self.extra_fields["txgio:bands"] = self.whcollection.get("txgio:bands")
        self.extra_fields["txgio:file_type"] = self.whcollection.get("txgio:file_type")
        self.extra_fields["txgio:resolution"] = self.whcollection.get("txgio:resolution")
        self.resolution = self.whcollection.get("txgio:resolution")

        #Setup providers
        txGIO = pystac.Provider(name="TxGIO", url="https://geographic.texas.gov/", description="Texas Geographic Information Office")
        self.providers = [txGIO]

        for provider in self.whcollection.get("providers"):
            obj = pystac.Provider(provider.get("name"), provider.get("description"), provider.get("roles"), provider.get("url"))
            self.providers.append(obj)

        self.license = self.whcollection.get("license")
        self.extra_fields["txgio:s_three_bucket_key"] = self.s3_key
        self.extra_fields["txgio:citation"] = "PLACEHOLDER"
        self.extra_fields["txgio:public"] = False
        self.extra_fields["txgio:availability"] = False
        self.extra_fields["txgio:last_modified"] = str(datetime.today())
        self.extra_fields["txgio:last_edited_by"] = self.whcollection.get("txgio:last_edited_by") or "PLACEHOLDER"
        self.extra_fields["txgio:template"] = self.whcollection.get("txgio:template") or "PLACEHOLDER"