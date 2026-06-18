from app.config.PathTyping import ItemPath

class TypeDescriptor(dict):
    description = ""
    media_type = ""
    usage = ""
    """
    Docstring for TypeDescriptor
    """
    def __init__(self, description: str, media_type: str, usage: str):
        super(TypeDescriptor, self).__init__()
        self['description'] = description
        self['media_type'] = media_type
        self['usage'] = usage

file_types: dict[str, TypeDescriptor] = {
    '.aux': TypeDescriptor("Metadata in aux format (Auxilary)", "text/plain", "metadata"),
    '.sdw': TypeDescriptor("Metadata in sdw format.", "application/vnd.stardivision.writer", "metadata"),
    '.xml': TypeDescriptor("Metadata in xml format.", "application/xml", "metadata"),
    '.txt': TypeDescriptor("Text file.", "text/plain", "metadata"),
    '.j2w': TypeDescriptor("Image file.", "application/octet-stream", "metadata"),
    '.jgwx': TypeDescriptor("JPEG world file (extended) for georeferencing", "text/plain", "metadata"),
    '.tfw': TypeDescriptor("TIFF world file for georeferencing", "text/plain", "metadata"),
    '.tif.ovr': TypeDescriptor("TIFF overview pyramids (reduced-resolution raster)", "application/octet-stream", "metadata"),
    '.aux.xml': TypeDescriptor("Auxilary metadata in xml format", "application/xml", "metadata"),
    '.jp2.aux.xml': TypeDescriptor("Auxilary metadata in xml format for .jp2 files", "application/xml", "metadata"),
    '.tif.aux.xml': TypeDescriptor("Auxilary metadata in xml format for .tif files", "application/xml", "metadata"),
    '.jpg.aux.xml': TypeDescriptor("Auxilary metadata in xml format for .jpg files", "application/xml", "metadata"),
    '.jpg.ovr': TypeDescriptor("Auxilary overview of jpen files", "application/octet-stream", "metadata"),
    '.aux.xml': TypeDescriptor("Auxilary metadata in xml format", "application/xml", "metadata"),
    '.tif.xml': TypeDescriptor("Metadata in xml format for .tif files", "application/xml", "metadata"),
    '.jp2.xml': TypeDescriptor("Metadata in xml format for .jp2 files", "application/xml", "metadata"),
    '.sid.aux.xml': TypeDescriptor("Auxilary metadata in xml format for .sid files", "application/xml", "metadata"),
    '.sid.xml': TypeDescriptor("Metadata in xml format for .sid files", "application/xml", "metadata"),
    
    '.sid': TypeDescriptor("MrSID raster image", "image/x-mrsid", "data"),
    '.zip': TypeDescriptor("Zip archive", "application/zip", "data"),
    '.tif': TypeDescriptor("Tif image", "image/tiff", "data"),
    '.laz': TypeDescriptor("Zipped Lidar", "application/vnd.las", "data"),
    '.img': TypeDescriptor("Raster Image file", "image/x-img", "data"),
    '.jp2': TypeDescriptor("Raster Image file", "image/jp2", "data"),
    '.tif': TypeDescriptor("GeoTIFF raster image", "image/tiff", "data"),
    '.jpg': TypeDescriptor("JPEG raster image", "image/jpeg", "data")}

def build_roles_for(resource: ItemPath):
    if resource.ext in file_types.keys():
        return {
            "ext": resource.ext,
            "roles": [resource.type, file_types[resource.ext], resource.ext]
        }
    else:
        print(f"Filetype {resource.ext} not found for stac_items in: {resource.path}")
