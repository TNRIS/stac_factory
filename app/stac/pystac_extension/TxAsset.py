import pystac

class TxAsset(pystac.Asset):
    # def __init__(self, file_type: str, rsc_path: str, title: str):
    def __init__(self, resource, collection_name: str, resolution: str | None, roles: list[str] | None = None, extra_fields={}):
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
        iama_type = "unknown" 

        if resource.ext == ".zip":
            iama_type = "application/zip"
        elif resource.ext == ".tif":
            iama_type = "image/tiff"
        elif resource.ext.endswith(".xml"):
            iama_type = "application/xml"
        elif resource.ext == ".laz":
            iama_type = "application/vnd.las"
        elif resource.ext == ".aux":
            iama_type = "text/x-stex"
        elif resource.ext == ".sdw":
            iama_type = "application/vnd.stardivision.writer"
        elif resource.ext == ".sid":
            iama_type = "image/x.mrsid"
        elif resource.ext == ".jp2":
            iama_type = "image/jp2"
        elif resource.ext == ".txt":
            iama_type = "text/plain"
        elif resource.ext == ".j2w":
            iama_type = "application/octet-stream"
        elif resource.ext == ".img":
            iama_type = "image/x-img"
        else:
            print("Unknown type.")

        super(TxAsset, self).__init__(
            href=f"/{resource.path}",
            title=collection_name,
            description= f'{resource.type} at resolution {resolution} for {resource.index} of {collection_name}',
            media_type=f"{iama_type}",
            extra_fields=extra_fields,
            roles=roles)
        self.stac_assets[collection_name] = self
        self.stac_assets['readable_name'] = resource.type