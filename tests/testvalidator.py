from stac_factory import S3Config, gen_local_stac_collection
from stac_factory import tx_types

DATA_WH_CONF = None
DATA_WH_CONF_HISTORIC = None

content_input = tx_types.ContentInput({"id": "stratmap-2021-land-parcels"})

whconf = S3Config(
    BUCKET_URL="http://test-gio-data-warehouse.s3-website-us-east-1.amazonaws.com/",
    BUCKET="test-gio-data-warehouse",
    ROOT="/root/factory_collections/input/",
    LOCAL=True,
    strip_slashes=False
)

gen_local_stac_collection(content_input, whconf)
