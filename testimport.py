from app.stac.build_stac import gen_this_stac_collection
import os
from app.root import ROOT

DATA_WH_CONF = None
DATA_WH_CONF_HISTORIC = None
if(os.path.exists(f"{ROOT}/config/config.py")):
    from app.config import DATA_WH_CONF_HISTORIC, DATA_WH_CONF
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
        'description': 'provided description',
        'txgio:categories': ["Imagery", "Historic Imagery", "Elevation"],
        'txgio:notes': 'provided txgio:notes',
        'txgio:spatial_keywords': 'provided txgio:spatial_keywords',
        'txgio:spatial_reference': 'provided txgio:spatial_reference',
        'txgio:bands': 'provided txgio:bands',
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

if(DATA_WH_CONF):
    gen_this_stac_collection(test_brown, DATA_WH_CONF)


# id
# txgio:publication_date?
# title
# txgio:banner_text?
# extent (will only have temporal data.  You'll have to add the bbox data)
# description
# txgio:categories (will have at least 1 set)
# txgio:notes?
# txgio:spatial_keywords?
# txgio:spatial_reference
# txgio:bands
# txgio:file_type
# txgio:resolution
# providers
# license
# item_assets
# assets
# keywords
# txgio:s_three_bucket_key