import datetime


class TxMeta(dict):
    def __init__(
        self,
        # required on create
        categories,
        spatial_reference,
        s_three_bucket_key,
        public,
        availability,
        template,
        # optional on create, but highly recommended before public flag is set to true
        publication_date=None,
        geometry=None,
        notes=None,
        resolution=None,
        bands=[],
        citation=None,
        spatial_keywords=None,
        banner_text=None,
        # Can be overwritten if wanted, but datetime.now() is fine.
        last_modified=datetime.datetime.now(),
        # Can be overwritten but can be Stac_Catalog if wanted
        last_edited_by="Stac Catalog",
    ):
        self.categories = categories
        self.spatial_reference = spatial_reference
        self.s_three_bucket_key = s_three_bucket_key
        self.public = public
        self.availability = availability
        self.template = template
        self.publication_date = (publication_date,)
        self.geometry = (geometry,)
        self.notes = (notes,)
        self.resolution = (resolution,)
        self.bands = (bands,)
        self.citation = (citation,)
        self.spatial_keywords = (spatial_keywords,)
        self.banner_text = (banner_text,)
        self.last_modified = (datetime.datetime.now(),)

        # Can be overwritten but can be Stac_Catalog if wanted
        self.last_edited_by = "Stac Catalog"
