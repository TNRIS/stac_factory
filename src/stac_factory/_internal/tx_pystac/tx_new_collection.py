import pystac
from datetime import datetime

from .tx_collection import TxCollection
from ..tx_aws.s_three import S3Collection
from ..util import log_info, log_exception
from ..tx_pystac import tx_types


class TxNewCollection(TxCollection):
    """
    Represents a STAC Collection built from a ContentInput definition.

    Initializes collection metadata, providers, temporal extent, and
    STAC items using values supplied in the ContentInput and the
    associated S3Collection. Metadata fields are populated from the
    ContentInput as well.

    Only ``id`` is required in the ContentInput. All other fields are
    optional.

    See the ContentInput TypedDict for supported fields and their expected
    types.
    """

    def __init__(
        self,
        content_input: tx_types.ContentInput,
        s3_collection: S3Collection,
        data_wh_configuration,
        stac_extensions: list[str] = [
            "https://test-gio-data-warehouse.s3.us-east-1.amazonaws.com/spec/schema.json",
            "https://stac-extensions.github.io/file/v2.1.0/schema.json",
        ],
    ):

        iso_temporals = (
            content_input.get("extent", {})
            .get("temporal", {})
            .get("interval", tx_types.default_extent)
        )

        temporals: list[list[datetime]] = []
        for temporal in iso_temporals:
            temporals.append(
                [
                    datetime.fromisoformat(temporal[0]),
                    datetime.fromisoformat(temporal[1]),
                ]
            )

        temporal = pystac.TemporalExtent(temporals)
        description = content_input.get("description", "")

        super().__init__(
            data_wh_configuration,
            s3_collection,
            content_input["id"],
            stac_extensions,
            temporal,
            description,
        )

        self.content_input = content_input
        self._build_metadata_from_input()
        self.build_stac_items()
        return

    def _build_metadata_from_input(self):
        """
        Populate collection metadata from the ContentInput.

        Collection properties such as license, resolution, providers; and
        STAC extra_fields, and TxGIO specific fields are initialized from the
        ContentInput. Default values are applied for fields that are not
        provided.
        """

        # Populate STAC fields from content_input, falling back to default
        # values when a field is not present.
        self.s3_key = self.content_input.get("id", "")
        self.license = self.content_input.get("license", "")

        # Map this extra_field, but not needed. Temporarily maintaining for compatibility. TODO: Remove later
        self.extra_fields["txgio:s_three_bucket_key"] = self.s3_key

        # Populate STAC extra_fields from content_input, falling back to
        # default values when a field is not present.
        extra_field_defaults = {
            "txgio:categories": [],
            "txgio:publication_date": "",
            "txgio:banner_text": "",
            "txgio:spatial_reference": [],
            "txgio:bands": [],
            "txgio:file_type": "",
            "txgio:citation": "",
            "txgio:public": False,
            "txgio:availability": False,
            "txgio:last_modified": "",
            "txgio:last_edited_by": "",
            "txgio:template": "",
            "txgio:notes": "",
            "txgio:spatial_keywords": "",
            "txgio:resolution": "",
        }

        for field, default in extra_field_defaults.items():
            self.extra_fields[field] = self.content_input.get(field, default)

        # Setup providers. An extra field requiring special handling.
        txGIO = pystac.Provider(
            name="TxGIO",
            url="https://geographic.texas.gov/",
            description="Texas Geographic Information Office",
        )
        self.providers = [txGIO]

        for provider in self.content_input.get("providers", []):
            obj = pystac.Provider(
                provider.get("name"),
                provider.get("description"),
                provider.get("roles"),
                provider.get("url"),
            )
            self.providers.append(obj)
