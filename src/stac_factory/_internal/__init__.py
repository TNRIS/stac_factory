# Setup tx_aws for extension
from .tx_aws.aws_types import ItemPath, AssetPath, DataWhPath, S3Config
from .tx_aws.s_three import (
    BucketClient,
    Client,
    S3Collection,
    WarehouseClient,
    LocalWarehouseClient,
)

_tx_aws = [
    "ItemPath",
    "AssetPath",
    "DataWhPath",
    "S3Config",
    "BucketClient",
    "Client",
    "Collection",
    "WarehouseClient",
    "LocalWarehouseClient",
]


# Setup tx_pypgstac for extension
from .tx_pypgstac.tx_loader import TxLoader

_tx_pypgstac = [
    "TxLoader",
]


# Setup tx_pystac for extension
from .tx_pystac.file_parsing import (
    TypeDescriptor,
    RoleBuilder,
    file_types,
)
from .tx_pystac.tx_asset import TxAsset
from .tx_pystac.tx_catalog import TxCatalog
from .tx_pystac.tx_item import TxItem
from .tx_pystac.tx_collection import TxCollection
from .tx_pystac.tx_new_collection import TxNewCollection
from .tx_pystac.tx_old_collection import TxOldCollection

_tx_pystac = [
    "TypeDescriptor",
    "build_roles_for",
    "file_types",
    "TxAsset",
    "TxCatalog",
    "TxItem",
    "TxCollection",
    "TxNewCollection",
    "TxOldCollection",
]


# Types Imports
from .tx_pystac.tx_types import (
    TypeProvider,
    TypeExtent,
    TypedDict,
    TileIndex,
    Category,
    default_extent,
)

_types = [
    "TypeProvider",
    "TypeExtent",
    "TypedDict",
    "TileIndex",
    "Category",
    "default_extent",
]


# Default export
__all__ = (
    ["tx_aws", "tx_pypgstac", "tx_pystac"],
    _tx_aws + _tx_pypgstac + _tx_pystac + _types,
)
