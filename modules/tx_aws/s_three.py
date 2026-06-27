import boto3, os
from typing import List
from types_boto3_s3.type_defs import ListObjectsV2OutputTypeDef
from types_boto3_s3 import Client
from pathlib import Path
from pandas import DataFrame

from app.config.PathTyping import DataWhPath, ItemPath, AssetPath


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

    # def get_contents(self):
    #     gdal.UseExceptions()
    #     vsicurl_path = f"/vsizip//vsis3/{DATA_WH_CONF.BUCKET}/{self.path}"

    #     try:
    #         zip_contents = gdal.ReadDirRecursive(vsicurl_path)
    #         if zip_contents:
    #             print(f"\nContents of '{vsicurl_path} include:\n")
    #             for item in zip_contents:
    #                 print(f"\t- {item}")
    #         else:
    #             print(f"No contents found or unable to access in {vsicurl_path}")
    #     except Exception as e:
    #         print(f"Error occurred attempting to read contents of {vsicurl_path}")
    #     else:
    #         self.contents = zip_contents
    #         return zip_contents

    def __str__(self):
        return f"{self.path}"

    def __repr__(self):
        return f"{self.path}"


class Collection:
    """
    A object representing a collection of resources
    """

    def __init__(self, resources):
        self.paths: DataWhPath
        self.index_asset: List[AssetPath] = []

        if len(resources):
            # Configure the common parts
            path_parts = Path(resources[0].path).parts
            root = path_parts[0]
            catalog_status = path_parts[1]
            historical_status = path_parts[2]
            collection_root = path_parts[3]
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

                    asset = AssetPath(
                        path=r.path,
                        type=type,
                        fname=fname,
                        ext=r.ext,
                        size=r.size,
                        etag=r.etag,
                        collection_name=r.collection_name,
                        checksum_algorithm=r.ChecksumAlgorithm[0],
                    )

                    if asset.type == "index":
                        if asset.fname.lower().endswith(".zip"):
                            self.index_asset.append(asset)
                        elif asset.fname.lower().endswith(".tif"):
                            self.index_asset.append(asset)
                    assets.append(asset)
                elif resource_type == "items":
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
                            r.ChecksumAlgorithm[0],
                        )
                    )

            self.paths = DataWhPath(
                root,
                catalog_status,
                historical_status,
                collection_root,
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
        self.client: Client = boto3.client("s3")
        self.root = self.s3config.ROOT
        self.archive_extension = self.s3config.ARCHIVE_EXTENSION

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
    A s3 bucket client with functions for accessing the data warehouse
    """

    def get_collections(self) -> List[Collection]:
        dirs_array = self.get_dirs(self.root, self.s3config.COLLECTION_ROOT)
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
            for dir in self.get_dirs(collection_name):  # self.archive_extension):
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

    # def collection_loop(self, callback):
    #     """
    #     Docstring for s3_warehouse_loop

    #     :param self: Description
    #     """
    #     s3_wh_colls: List[Collection] = self.get_all_data_warehouse_collections()
    #     for wh_collection in s3_wh_colls:
    #         callback(wh_collection)

    def get_filename_path(self, rsc_path):
        """Get file name path in s3 bucker."""
        return f"{self.s3config.BUCKET_URL}{rsc_path}"

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
