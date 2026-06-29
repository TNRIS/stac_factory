from stac_factory.build_stac import gen_this_stac_collection
from modules.tx_aws.aws_types import S3Config
from modules.tx_pystac.tx_types import ContentInput, TypeExtent, TypeProvider

DATA_WH_CONF = None
DATA_WH_CONF_HISTORIC = None

test_brown = ContentInput(
    **{
        "id": "stratmap-2019-50cm-brown-county",
        "title": "provided_title",
        "description": "123123123123",
        "txgio:publication_date": "provided publication_date",
        "txgio:banner_text": "provided banner_text",
        "extent": TypeExtent(
            spatial={"bbox": []},
            temporal={"interval": [["2016-12-15T00:00:00Z", "2016-12-15T00:00:00Z"]]},
        ),
        "txgio:categories": ["Imagery", "Historic Imagery", "Elevation"],
        "txgio:notes": "provided notes",
        "txgio:spatial_keywords": "provided spatial_keywords",
        "txgio:spatial_reference": ["provided spatial_reference", "thing1", "thing2"],
        "txgio:bands": ["provided bands", "thing1", "thing2"],
        "txgio:file_type": "provided file_type",
        "txgio:resolution": "provided resolution",
        "providers": [
            TypeProvider(
                name="United States Department of the Interior",
                description="United States Department of the Interior (DOI) data can be accessed at NULL. For questions or comments please reach out to the data contact at  or visit their website at https://www.doi.gov/",
                url="https://www.doi.gov/",
                roles=[],
            ),
            TypeProvider(
                name="United States Army Corps of Engineers",
                description="United States Army Corps of Engineers (USACE) data can be accessed at NULL. For questions or comments please reach out to the data contact at  or visit their website at https://www.usace.army.mil",
                url="https://www.usace.army.mil",
                roles=[],
            ),
        ],
        "license": "CC0",
        "keywords": ["thing1", "thing2"],
        "txgio:s_three_bucket_key": "some/key/path",
        "txgio:public": True,
        "txgio:availability": True,
        "txgio:last_modified": "2024-01-01",
        "txgio:last_edited_by": "user@example.com",
        "txgio:template": "default",
        "txgio:collection_id": None,
        "txgio:geometry": None,
        "txgio:scale": None,
        "txgio:citation": None,
    }
)

whconf = S3Config(
    BUCKET_URL="http://test-gio-data-warehouse.s3-website-us-east-1.amazonaws.com/",
    BUCKET="test-gio-data-warehouse",
    ROOT="data/cataloged/general/collections/",
    ARCHIVE_EXTENSION=".zip",
    COLLECTION_ROOT="/",
)

gen_this_stac_collection(test_brown, whconf)
