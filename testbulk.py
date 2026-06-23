from app.stac.build_stac import gen_stac_collection
from app.config.S3Config import S3Config

whconf = S3Config(
    BUCKET_URL = "http://test-gio-data-warehouse.s3-website-us-east-1.amazonaws.com/",
    BUCKET = "test-gio-data-warehouse",
    ROOT='data/cataloged/general/collections/',
    ARCHIVE_EXTENSION=".zip",
    COLLECTION_ROOT="/")
if __name__ == '__main__':
    gen_stac_collection(whconf)
