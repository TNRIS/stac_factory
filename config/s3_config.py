class S3Config:
    BUCKET_URL: str = ""

    # Params are overridable in constructor.
    def __init__(
        self, BUCKET_URL, BUCKET="", ROOT="", ARCHIVE_EXTENSION="", COLLECTION_ROOT=""
    ):
        self.BUCKET_URL = BUCKET_URL
        self.BUCKET = BUCKET
        self.ROOT = ROOT
        self.ARCHIVE_EXTENSION = ARCHIVE_EXTENSION
        self.COLLECTION_ROOT = COLLECTION_ROOT


DATA_WH_CONF = S3Config(
    BUCKET_URL="", BUCKET="", ROOT="", ARCHIVE_EXTENSION="", COLLECTION_ROOT=""
)