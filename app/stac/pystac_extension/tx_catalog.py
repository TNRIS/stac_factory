import pystac
import typing


class TxCatalog(pystac.Catalog):
    """
    Docstring for TxCatalog
    Update the constructor for use in TxGIO
    """

    def __init__(
        self,
        id: str = "https://data.tnris.org",
        description: str = "Stac Catalog for TxGIO Datahub",
        title: str | None = "TxGIO Datahub",
        stac_extensions: list[str] | None = None,
        extra_fields: dict[str, typing.Any] | None = None,
        href: str | None = "/catalog",
        catalog_type: pystac.CatalogType = pystac.CatalogType.SELF_CONTAINED,
    ):
        super().__init__(
            id, description, title, stac_extensions, extra_fields, href, catalog_type
        )
