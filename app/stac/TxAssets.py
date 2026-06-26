import pystac


class AssetException(Exception):
    pass


class TxAsset(pystac.Asset):
    """
    Docstring for TxAsset

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

    def __init__(
        self, file_type: str, rsc_path: str, title: str
    ) -> dict[str, pystac.Asset]:

        stac_assets: dict[str, pystac.Asset] = {}
        stac_asset = pystac.Asset(
            href=rsc_path,
            title=title,
            description=f"{file_type} file",
            media_type=f"{file_type}",
        )
        stac_assets[title] = stac_asset

        return stac_assets
