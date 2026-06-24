from app.stac.build_stac import gen_this_stac_collection
from app.config.S3Config import S3Config

DATA_WH_CONF = None
DATA_WH_CONF_HISTORIC = None

test_brown = {
    'id': 'stratmap-2019-50cm-brown-county',
    'title': 'provided_title',
    'txgio:publication_date': 'provided publication_date',
    'txgio:banner_text': 'provided banner_text',
    "extent": {
        "spatial": {
            "bbox": []
        },
        "temporal": {
            "interval": [
                [
                    "2016-12-15T00:00:00Z",
                    "2016-12-15T00:00:00Z"
                ]
            ]
        }
    },
    'description': '123123123123',
    'txgio:categories': ["Imagery", "Historic Imagery", "Elevation"],
    'txgio:notes': 'provided txgio:notes',
    'txgio:spatial_keywords': 'provided txgio:spatial_keywords',
    'txgio:spatial_reference': ['provided txgio:spatial_reference', 'thing1', 'thing2'],
    'txgio:bands': ['provided txgio:bands', 'thing1', 'thing2'],
    'txgio:file_type': 'provided txgio:file_type',
    'txgio:resolution': 'provided txgio:resolution',
    'providers': [
        {
            "name": "United States Department of the Interior",
            "description": "United States Department of the Interior (DOI) data can be accessed at NULL. For questions or comments please reach out to the data contact at  or visit their website at https://www.doi.gov/",
            "url": "https://www.doi.gov/",
            "roles": [],
        },
        {
            "name": "United States Army Corps of Engineers",
            "description": "United States Army Corps of Engineers (USACE) data can be accessed at NULL. For questions or comments please reach out to the data contact at  or visit their website at https://www.usace.army.mil",
            "url": "https://www.usace.army.mil",
            "roles": []
        }
    ],
    'license': 'CC0',
    'keywords': ["thing1", "thing2"]
}
whconf = S3Config(
    BUCKET_URL = "http://test-gio-data-warehouse.s3-website-us-east-1.amazonaws.com/",
    BUCKET = "test-gio-data-warehouse",
    ROOT='data/cataloged/general/collections/',
    ARCHIVE_EXTENSION=".zip",
    COLLECTION_ROOT="/")

gen_this_stac_collection(test_brown, whconf)