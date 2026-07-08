from ..util import log_info
from osgeo import gdal
from pathlib import Path


class TypeDescriptor(dict):
    """
    Docstring for TypeDescriptor
    """

    def __init__(self, description: str, media_type: str, usage: str):
        super(TypeDescriptor, self).__init__()
        self["description"] = description
        self["media_type"] = media_type
        self["usage"] = usage


file_types: dict[str, TypeDescriptor] = {
    ".aux": TypeDescriptor(
        "Metadata in aux format (Auxilary)", "text/plain", "metadata"
    ),
    ".sdw": TypeDescriptor(
        "Metadata in sdw format.", "application/vnd.stardivision.writer", "metadata"
    ),
    ".xml": TypeDescriptor("Metadata in xml format.", "application/xml", "metadata"),
    ".txt": TypeDescriptor("Text file.", "text/plain", "metadata"),
    ".j2w": TypeDescriptor("Image file.", "application/octet-stream", "metadata"),
    ".jgwx": TypeDescriptor(
        "JPEG world file (extended) for georeferencing", "text/plain", "metadata"
    ),
    ".tfw": TypeDescriptor(
        "TIFF world file for georeferencing", "text/plain", "metadata"
    ),
    ".tif.ovr": TypeDescriptor(
        "TIFF overview pyramids (reduced-resolution raster)",
        "application/octet-stream",
        "metadata",
    ),
    ".aux.xml": TypeDescriptor(
        "Auxilary metadata in xml format", "application/xml", "metadata"
    ),
    ".jp2.aux.xml": TypeDescriptor(
        "Auxilary metadata in xml format for .jp2 files", "application/xml", "metadata"
    ),
    ".tif.aux.xml": TypeDescriptor(
        "Auxilary metadata in xml format for .tif files", "application/xml", "metadata"
    ),
    ".jpg.aux.xml": TypeDescriptor(
        "Auxilary metadata in xml format for .jpg files", "application/xml", "metadata"
    ),
    ".jpg.ovr": TypeDescriptor(
        "Auxilary overview of jpen files", "application/octet-stream", "metadata"
    ),
    ".aux.xml": TypeDescriptor(
        "Auxilary metadata in xml format", "application/xml", "metadata"
    ),
    ".tif.xml": TypeDescriptor(
        "Metadata in xml format for .tif files", "application/xml", "metadata"
    ),
    ".jp2.xml": TypeDescriptor(
        "Metadata in xml format for .jp2 files", "application/xml", "metadata"
    ),
    ".sid.aux.xml": TypeDescriptor(
        "Auxilary metadata in xml format for .sid files", "application/xml", "metadata"
    ),
    ".sid.xml": TypeDescriptor(
        "Metadata in xml format for .sid files", "application/xml", "metadata"
    ),
    ".pdf": TypeDescriptor("PDF document", "application/pdf", "metadata"),
    ".docx": TypeDescriptor(
        "Microsoft Word document (Open XML format)",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "metadata",
    ),
    ".doc": TypeDescriptor(
        "Microsoft Word document (legacy binary format)",
        "application/msword",
        "metadata",
    ),
    ".prj": TypeDescriptor(
        "Projection definition for ESRI Shapefile",
        "text/plain",
        "metadata",
    ),
    ".cpg": TypeDescriptor(
        "Character encoding definition for ESRI Shapefile",
        "text/plain",
        "metadata",
    ),
    ".sid": TypeDescriptor("MrSID raster image", "image/x-mrsid", "data"),
    ".zip": TypeDescriptor("Zip archive", "application/zip", "data"),
    ".tif": TypeDescriptor("Tif image", "image/tiff", "data"),
    ".laz": TypeDescriptor("Zipped Lidar", "application/vnd.las", "data"),
    ".img": TypeDescriptor("Raster Image file", "image/x-img", "data"),
    ".jp2": TypeDescriptor("Raster Image file", "image/jp2", "data"),
    ".tif": TypeDescriptor("GeoTIFF raster image", "image/tiff", "data"),
    ".jpg": TypeDescriptor("JPEG raster image", "image/jpeg", "data"),
    ".shp": TypeDescriptor(
        "ESRI Shapefile geometry data",
        "application/x-shapefile",
        "data",
    ),
    ".dbf": TypeDescriptor(
        "dBase attribute table for ESRI Shapefile",
        "application/vnd.dbase",
        "data",
    ),
    ".shx": TypeDescriptor(
        "ESRI Shapefile geometry index",
        "application/octet-stream",
        "data",
    ),
}


class RoleBuilder:
    """Builds STAC roles for resources and caches ZIP role lookups."""

    def __init__(self, s3_bucket_url: str):
        """
        Initialize the role builder.

        Args:
            s3_bucket_url: S3 bucket URL used for zip inspection.
        """
        self.s3_bucket_url = s3_bucket_url
        self.zip_role_store: dict[str, list[str]] = {}

    def build_roles_for(self, resource, uniform_zip: bool = False) -> list[str]:
        """
        Build a list of STAC roles for a resource.

        For ZIP files, attempts to determine contained file types from the
        filename or archive contents. When uniform_zip is True, roles may
        be reused for ZIP files of the same resource type.

        Args:
            resource: Resource to generate roles for.
            uniform_zip: Indicates that ZIP files of the same resource
                type are expected to contain identical contents, allowing
                cached roles to be reused.

        Returns:
            Ordered list of unique roles.

        Raises:
            ValueError: If the resource file type is unsupported.
        """

        zip_roles: list[str] = []
        if resource.ext == ".zip":
            try:
                if uniform_zip and resource.type in self.zip_role_store:
                    return self.zip_role_store[resource.type]

                # Was told maybe they'd have file type info after the underscore. So gonna check.
                postzip = resource.fname.split("_")[-1]
                maybeftype = f".{postzip.removesuffix('.zip')}"
                if maybeftype in file_types:
                    zip_roles.append(maybeftype)
                else:
                    # Try to deduce from the files inside.
                    vsi_path = f"/vsizip//vsicurl/{self.s3_bucket_url}/{resource.path}"
                    dirs = gdal.listdir(vsi_path) or []

                    for d in dirs:
                        if hasattr(d, "name") and isinstance(d.name, str):
                            path = Path(d.name)
                            ext = "".join(path.suffixes)
                            if ext in file_types:
                                zip_roles.append(ext)
            except Exception as e:
                log_info(
                    f"Error trying to deduce the zip filetype for {resource.fname}", e
                )

        if resource.ext in file_types:
            roles = list(file_types[resource.ext].values())
            roles.append(resource.ext)
            roles.append(resource.type)
            roles.extend(zip_roles)

            unique_roles = list(dict.fromkeys(roles))
            if resource.ext == ".zip" and uniform_zip:
                self.zip_role_store[resource.type] = unique_roles
            return unique_roles
        else:
            raise ValueError(
                f"Filetype {resource.ext} not found for stac_items in: {resource.path}"
            )
