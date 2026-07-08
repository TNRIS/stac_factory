from stac_factory import gen_stac_collection, S3Config

whconf = S3Config(
    BUCKET_URL="http://test-gio-data-warehouse.s3-website-us-east-1.amazonaws.com/",
    BUCKET="test-gio-data-warehouse",
    ROOT="data/cataloged/general/collections/",
)
if __name__ == "__main__":
    gen_stac_collection(whconf)
