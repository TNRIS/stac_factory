from enum import Enum
from logging import root
from typing import List


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
    COLLECTION_ROOT: str = ""
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
        collection_root,
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
        self.COLLECTION_ROOT = collection_root
        self.ASSETS_ROOT = assets_root
        self.ITEMS_ROOT = items_root
        self.ASSETS = assets
        self.ITEMS = items
