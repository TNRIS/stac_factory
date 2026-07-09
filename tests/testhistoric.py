from stac_factory import S3Config, gen_this_stac_collection
from stac_factory import tx_types

DATA_WH_CONF = None
DATA_WH_CONF_HISTORIC = None

# This ContentInput Typed Dict is meant to test a specific id
# example: TXDOT-1981-347557
content_input = tx_types.ContentInput({"id": "TXDOT-1981-347557"})

whconf = S3Config(
    BUCKET_URL="http://test-gio-data-warehouse.s3-website-us-east-1.amazonaws.com/",
    BUCKET="test-gio-data-warehouse",
    ROOT="data/cataloged/historic/collections/",
)

gen_this_stac_collection(content_input, whconf)
