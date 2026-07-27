import boto3, os
from botocore.config import Config
from typing import List
from types_boto3_s3.type_defs import ListObjectsV2OutputTypeDef
from types_boto3_s3 import Client
from pathlib import Path
from pandas import DataFrame
from .aws_types import DataWhPath, ItemPath, AssetPath


class Resource:
    """ """

    def __init__(self, path, collection_name: str):
        self.path = path.Key
        self.collection_name = collection_name
        self.contents = []

        p = Path(self.path)

        self.ext = "".join(p.suffixes)
        self.ChecksumAlgorithm = path.ChecksumAlgorithm
        self.etag = path.ETag
        self.size = path.Size
        self.type = Path(self.path).parts[-2]
        self.filename = os.path.splitext(os.path.split(self.path)[1])[0]

    def __str__(self):
        return f"{self.path}"

    def __repr__(self):
        return f"{self.path}"


class S3Collection:
    """
    Represents a single Data Warehouse collection.

    A S3Collection groups the assets and items that belong to a collection.
    During initialization, warehouse resources are parsed from their s3
    paths and converted into AssetPath and ItemPath objects.

    Attributes:
        paths:
            DataWhPath describing the collection's location within the
            Data Warehouse hierarchy

        index_asset:
            The collection's index asset used to map individual items to the
            tile index.
            Each collection must contain exactly one index asset.
    """

    def __init__(self, resources):
        self.paths: DataWhPath
        self.index_asset: AssetPath

        if len(resources):
            # Configure the common parts
            path_parts = Path(resources[0].path).parts
            root = path_parts[0]
            catalog_status = path_parts[1]
            historical_status = path_parts[2]
            collection_id = path_parts[4]
            assets: List[AssetPath] = []  # NOTE
            items: List[ItemPath] = []  # NOTE
            df = DataFrame(resources)
            for r in df.itertuples():
                s = r
                r = r[1]
                resource_parts = Path(r.path).parts
                resource_type: str = resource_parts[5]

                if resource_type == "assets":
                    # WORKAROUND 1: Not all assets have the same directory structure (Statewide.) can be removed if we put statewide assets in assets/statewide/FOO.zip
                    if (
                        len(resource_parts) == 7
                    ):  # If directory parts is only 7 then this asset is statewide so check.
                        type = "statewide"
                        fname = resource_parts[6]
                    else:  # Otherwise the asset type is indicated by the directory structure.
                        type = resource_parts[6]
                        fname = resource_parts[7]
                    # End of WORKAROUND 1

                    checksum = (
                        r.ChecksumAlgorithm[0]
                        if r.ChecksumAlgorithm
                        else None
                    )

                    asset = AssetPath(
                        path=r.path,
                        type=type,
                        fname=fname,
                        ext=r.ext,
                        size=r.size,
                        etag=r.etag,
                        collection_name=r.collection_name,
                        checksum_algorithm=checksum,
                    )

                    if asset.type == "index":
                        self.index_asset = asset

                    assets.append(asset)
                elif resource_type == "items":
                    checksum = (
                        r.ChecksumAlgorithm[0]
                        if r.ChecksumAlgorithm
                        else None
                    )

                    items.append(
                        ItemPath(
                            r.path,
                            resource_parts[6],
                            r.type,
                            f"{r.filename}{r.ext}",
                            r.ext,
                            r.size,
                            r.etag,
                            r.collection_name,
                            checksum,
                        )
                    )

            self.paths = DataWhPath(
                root,
                catalog_status,
                historical_status,
                collection_id,
                "assets",
                "items",
                assets,
                items,
            )


class BucketClient:
    """
    A bucket with a s3 client.
    """

    def __init__(self, s3config):
        self.s3config = s3config
        self.name = self.s3config.BUCKET
        self.url = self.s3config.BUCKET_URL
        self.client: Client = boto3.client(
            "s3", config=Config(connect_timeout=5, read_timeout=30)
        )
        self.root = self.s3config.ROOT

    def get_dirs(
        self, prefix: str, delimiter: str | None = None
    ) -> List[ListObjectsV2OutputTypeDef]:
        """
        Return a list of strings representing directories in a s3 bucket provided by bucket.
        """
        kwargs = {"Bucket": self.name, "Prefix": prefix}
        if delimiter:
            kwargs["Delimiter"] = delimiter

        dirs: List[str] = []

        def list_dirs(kwargs, continuation_token=False) -> ListObjectsV2OutputTypeDef:
            if continuation_token:
                kwargs["ContinuationToken"] = continuation_token
            return self.client.list_objects_v2(**kwargs)

        dirs = []
        dirs.append(list_dirs(kwargs))
        while dirs[-1].get("IsTruncated"):
            cont = list_dirs(kwargs, dirs[-1].get("NextContinuationToken"))
            dirs.append(cont)

        return dirs

    def upload(self, key, body):
        self.client.put_object(Bucket=self.name, Key=key, Body=body)


class WarehouseClient(BucketClient):
    """
    Client for accessing Data Warehouse content stored in S3.

    Extends BucketClient with functionality for:

    - Discovering available collections.
    - Retrieving collection resources from S3.
    - Building Collection objects from warehouse resources.
    - Generating S3 and VSI-compatible resource paths.
    """

    def get_collections(self) -> List[Collection]:
        dirs_array = self.get_dirs(self.root + "/", delimiter="/")
        collection_names = []

        for dir in dirs_array:
            for ob in dir.get("CommonPrefixes"):
                collection_names.append(ob.get("Prefix"))

        return collection_names

    def get(self, collection_name) -> List[Collection]:
        resources = []

        dirs = self.get_dirs(collection_name)
        for dir in dirs:
            items = DataFrame(dir.get("Contents"))
            for wh in items.itertuples(index=True):
                if wh.Size > 0:
                    resources.append(Resource(path=wh, collection_name=collection_name))

        return resources

    def build_collections(self) -> List[Collection]:
        """
        Build a list of collections based on the configuration which defaults to self.s3_config
        """
        collections: List[Collection] = []
        collection_names = []

        dirs_array = self.get_dirs(self.root, self.s3config.COLLECTION_ROOT)
        for dir in dirs_array:

            for ob in dir.get("CommonPrefixes"):
                collection_names.append(ob.get("Prefix"))

        for collection_name in collection_names:
            cIndex = -2  # Collection Name index
            paths = []
            for dir in self.get_dirs(collection_name):
                if not "Contents" in dir:
                    continue

                for content in dir.get("Contents"):
                    if not "Contents" in dir:
                        continue
                    paths.append(content)

                if len(collection_name.split("/")) > 1:
                    collection_name = collection_name.split("/")[cIndex]

                resources = []
                for path in paths:
                    if len(path.get("Key").split("/")) >= 8:
                        resources.append(
                            Resource(path=path, collection_name=collection_name)
                        )
                collections.append(Collection(resources))

        return collections

    def get_all_data_warehouse_collections(self) -> List[Collection]:
        """
        Return all collections from data warehouse.
        """
        s3_collections: List[Collection] = self.build_collections()

        if not s3_collections:
            raise (
                IndexError(
                    f"There are no resources in the collection: {s3_collections.name}"
                )
            )

        return s3_collections

    def get_filename_path(self, rsc_path):
        """Get file name path in s3 bucker."""
        return f"{self.s3config.BUCKET_URL}/{rsc_path}"

    def get_vsicurl_path(self, rsc_path: str) -> str:
        """
        get a url from a s3 path formatted for vsicurl.
        """
        return f"/vsizip//vsicurl/{self.get_filename_path(rsc_path)}"

    def get_vsicurl_lpc_path(self, rsc_path: str, filename: str) -> str:
        """
        get a url from a s3 path formatted for vsicurl. Specifically the lidar pointcloud metadata.
        """
        return f"{self.get_vsicurl_path(rsc_path) }"

    def __init__(self, s3config):
        super().__init__(s3config)


class LocalWarehouseClient:
    """
    Client for accessing Data Warehouse content stored locally.

    Extends local filesystem access with functionality for:

    - Discovering available collections.
    - Retrieving collection resources.
    - Building LocalCollection objects.
    - Generating local resource paths.
    """

    def __init__(self, config):
        self.config = config
        self.root = Path(config.ROOT)

    def get_collections(self) -> List:
        """
        Return all collection names under the warehouse root.
        """

        if not self.root.exists():
            return []

        return [p.name for p in self.root.iterdir() if p.is_dir()]

    def get(self, collection_name) -> List:
        """
        Return Resource objects for all files in a collection.
        """

        resources = []

        collection_path = Path(collection_name)

        if not collection_path.exists():
            collection_path = self.root / collection_name

        if not collection_path.exists():
            return resources

        for file_path in collection_path.rglob("*"):
            if file_path.is_file():
                from types import SimpleNamespace
                import hashlib

                
                md5 = hashlib.md5()

                with open(file_path, "rb") as f:
                    for chunk in iter(lambda: f.read(8192), b""):
                        md5.update(chunk)

                md5_hex = md5.hexdigest()

                resources.append(
                    Resource(
                        path=SimpleNamespace(
                            Key=str(file_path),
                            ChecksumAlgorithm=["MD5"],
                            ETag=md5_hex,
                            Size=file_path.stat().st_size,
                        ),
                        collection_name=collection_path.name,
                    )
                )


        return resources

    def build_collections(self) -> List:
        """
        Build LocalCollection objects from the configured warehouse root.
        """

        collections = []

        for collection_name in self.get_collections():

            resources = self.get(collection_name)

            if resources:
                collections.append(LocalCollection(resources))

        return collections

    def get_all_data_warehouse_collections(self) -> List:
        """
        Return all collections in the local warehouse.
        """

        collections = self.build_collections()

        if not collections:
            raise IndexError(f"No collections found under {self.root}")

        return collections

    def get_filename_path(self, rsc_path):
        """
        Return the absolute path to a resource.
        """

        return str(Path(rsc_path).resolve())

    def get_local_path(self, rsc_path: str) -> str:
        """
        Return a filesystem path suitable for local processing.
        """

        return str(Path(rsc_path).resolve())

    def get_local_lpc_path(
        self,
        rsc_path: str,
        filename: str,
    ) -> str:
        """
        Return a local path for lidar point-cloud resources.
        """

        return str(Path(rsc_path).resolve())
