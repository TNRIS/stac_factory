from app.stac.build_stac import gen_this_stac_collection
from app.config.config import DATA_WH_CONF

test_brown = {
    'id': 'stratmap-2024-50cm-archer-jack-lampasas-smith-counties',
    'title': 'provided_title',
    'txgio:publication_date': 'provided publication_date',
    'txgio:banner_text': 'provided banner_text',
    'extent': 'provided extent',
    'description': 'provided description',
    'txgio:categories': 'provided categories',
    'txgio:notes': 'provided txgio:notes',
    'txgio:spatial_keywords': 'provided txgio:spatial_keywords',
    'txgio:spatial_reference': 'provided txgio:spatial_reference',
    'txgio:bands': 'provided txgio:bands',
    'txgio:file_type': 'provided txgio:file_type',
    'txgio:resolution': 'provided txgio:resolution',
    'providers': 'provided providers',
    'license': 'provided license',
    'item_assets': 'provided item_assets',
    'assets': 'provided assets',
    'keywords': 'provided keywords',
    'txgio:s_three_bucket_key': 'provided txgio:s_three_bucket_key'    
}

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