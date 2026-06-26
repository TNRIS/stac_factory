import pystac


class TxAsset(pystac.Asset):
    # def __init__(self, file_type: str, rsc_path: str, title: str):
    def __init__(
        self,
        resource,
        collection_name: str,
        resolution: str | None,
        roles: list[str] = [],
        extra_fields={},
    ):
        """
        Docstring for assets_builder

        :param self: pystac.Asset
        :param file_type: File type of the resource ex: shp
        :type file_type: str
        :param rsc_path: The path to the resource in the datahub s3 bucket for the asset.
        :type rsc_path: str
        :param title: Title of the asset
        :type title: str
        :return: returns a pystac.Asset built with the parameters provided.
        :rtype: dict[str, Asset]
        """
        self.stac_assets = {}

        super(TxAsset, self).__init__(
            href=f"/{resource.path}",
            title=collection_name,
            description=f"{resource.type} at resolution {resolution} for {resource.index} of {collection_name}",
            media_type=f"{resource.type}",
            extra_fields=extra_fields,
            roles=roles,
        )
        self.stac_assets[collection_name] = self
        self.stac_assets["readable_name"] = resource.type
