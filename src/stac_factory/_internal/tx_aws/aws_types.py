class AssetPath:
    path: str = ""
    type: str = ""
    fname: str = ""
    ext = ""
    size = ""
    etag = ""
    collection_name = ""
    checksum_algorithm = ""

    def __init__(
        self, path, type, fname, ext, size, etag, collection_name, checksum_algorithm
    ):
        self.path = path
        self.type = type
        self.fname = fname
        self.ext = ext
        self.size = size
        self.etag = etag
        self.collection_name = collection_name
        self.checksum_algorithm = checksum_algorithm


class ItemPath:
    path: str = ""
    index: str = ""
    type: str = ""
    fname: str = ""

    def __init__(
        self,
        path,
        index,
        type,
        fname,
        ext,
        size,
        etag,
        collection_name,
        checksum_algorithm,
    ):
        self.path = path
        self.index = index
        self.type = type
        self.fname = fname
        self.ext = ext
        self.size = size
        self.etag = etag
        self.collection_name = collection_name
        self.checksum_algorithm = checksum_algorithm


class DataWhPath:
    """
    Docstring for DataWhPath
    """

    ROOT: str = ""
    CATALOGUED_STATUS: str = ""  # I don't worry about uncatalogued data at the moment.
    HISTORIC_STATUS: str = ""
    COLLECTIONS_ROOT: str = ""
    ASSETS_ROOT = "assets"
    ITEMS_ROOT = "items"
    ASSETS = None
    ITEMS = None

    def __init__(
        self,
        root,
        catalog_status,
        historic_status,
        collections_root,
        assets_root,
        items_root,
        assets,
        items,
    ):
        self.ROOT = root
        self.CATALOGUED_STATUS = (
            catalog_status  # I don't worry about uncatalogued data at the moment.
        )
        self.HISTORIC_STATUS = historic_status
        self.COLLECTIONS_ROOT = collections_root
        self.ASSETS_ROOT = assets_root
        self.ITEMS_ROOT = items_root
        self.ASSETS = assets
        self.ITEMS = items


class S3Config:
    """
    Leading and trailing slashes are stripped by default to prevent accidental
    absolute-path behavior when constructing S3 object paths.
    Disable only if you are certain leading slashes are required.
    """

    def _strip(self, path: str) -> str:
        return path.strip("/")

    # Params are overridable in constructor.
    def __init__(
        self,
        BUCKET_URL: str = "",
        BUCKET: str = "",
        ROOT: str = "",
        strip_slashes: bool = True,
    ):
        if strip_slashes:
            self.BUCKET_URL = self._strip(BUCKET_URL)
            self.BUCKET = self._strip(BUCKET)
            self.ROOT = self._strip(ROOT)
        else:
            self.BUCKET_URL = BUCKET_URL
            self.BUCKET = BUCKET
            self.ROOT = ROOT
