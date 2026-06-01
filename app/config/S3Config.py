from .PathTyping import DataWhPath

class S3Config:
    BUCKET_URL:str = ""
    
    # Params are overridable in constructor. 
    def __init__(self,
                BUCKET_URL,
                BUCKET = "",
                PREFIX = "",
                LCD_COLLECTION_PREFIX = "",
                LORE_COLLECTION_PREFIX = "",
                RESOURCES_KEY = "",
                ROOT = "",
                ARCHIVE_EXTENSION = "",
                COLLECTION_ROOT = "",
                DATA_WH_PATH : DataWhPath | None = None):
        self.BUCKET_URL = BUCKET_URL
        self.BUCKET = BUCKET
        self.PREFIX = PREFIX
        self.LCD_COLLECTION_PREFIX = LCD_COLLECTION_PREFIX
        self.LORE_COLLECTION_PREFIX = LORE_COLLECTION_PREFIX
        self.RESOURCES_KEY = RESOURCES_KEY
        self.ROOT = ROOT
        self.ARCHIVE_EXTENSION = ARCHIVE_EXTENSION
        self.COLLECTION_ROOT = COLLECTION_ROOT
        self.DATA_WH_PATH = DATA_WH_PATH

class GeosConfig:
    VECTOR_EXTS = ["shp", "parquet", "pq", "gdb", "fgb", "fgdb"]
    RASTER_EXTS = ["tiff", "tif", "geotif", "geotiff", "img", "mrsid", "jpg", "jpeg", "jpeg2000"]
    POINT_CLOUD_EXTS = ["laz", "las", "copc"]