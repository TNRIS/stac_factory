import shapely, json
from typing import TypedDict, Required, NotRequired, Literal, Any
from geopandas import GeoDataFrame
from shapely.geometry.base import BaseGeometry

from ..util import log_exception


class TileIndex:
    outline: str
    dict: dict
    simplify: BaseGeometry

    def __init__(self, panda_layer: GeoDataFrame):
        """
        Docstring for __init__
        This builds a outline, and a dict. The dict is a dictionary
        epresentation of geopandas, and outline is geojson formatted
        outline of the layer, that is unioned, and simplified at
        0.0001 degrees (Roughly 100M)

        :param self: self
        :param panda_layer: Just a GeoPandas Data Frame.
        :type panda_layer: GeoDataFrame
        """
        try:
            # footprint of a collection as a .geojson file format. Must be of type Polygon or MultiPolygon. Please simplify geometries prior to uploading using either the Douglas-Peucker algorithm with .0001 tolerance, or Wang-Muller algorithm with .0005 tolerance.
            union = panda_layer.union_all(
                grid_size=0.0001
            )  # Create a grid of ~100M, just to get a practical file size.
            self.simplify = union.simplify(
                tolerance=0.0001, preserve_topology=True
            )  # Defaults to Douglas Peucker, recommended in api for the_geom.
            self.outline = json.loads(shapely.to_geojson(self.simplify, indent=0))
            self.dict = panda_layer.to_dict()
        except Exception as e:
            log_exception(e)


# categories (from json schema)
Category = Literal[
    "Imagery",
    "Historic Imagery",
    "Elevation",
    "Basemap",
    "Hydrography",
    "Boundaries",
    "Statewide",
    "Archived",
]


class TypeProvider(TypedDict):
    name: Required[str]
    description: NotRequired[str]
    url: NotRequired[str]
    roles: NotRequired[list[str]]


class TypeExtent(TypedDict):
    spatial: Required[dict[str, Any]]
    temporal: Required[dict[str, list[list[str]]]]


ContentInput = TypedDict(
    "ContentInput",
    {
        "id": Required[str],
        "title": Required[str],
        "description": Required[str],
        "txgio:publication_date": NotRequired[str],
        "txgio:banner_text": NotRequired[str],
        "txgio:notes": NotRequired[str],
        "txgio:spatial_keywords": NotRequired[str],
        "txgio:categories": Required[list[Category]],
        "keywords": NotRequired[list[str]],
        "extent": NotRequired[TypeExtent],
        "txgio:spatial_reference": Required[list[str]],
        "txgio:bands": NotRequired[list[str]],
        "txgio:resolution": NotRequired[str],
        "txgio:file_type": NotRequired[str],
        "providers": NotRequired[list[TypeProvider]],
        "license": NotRequired[str],
        "txgio:collection_id": NotRequired[str | None],
        "txgio:geometry": NotRequired[dict[str, Any]],
        "txgio:scale": NotRequired[str | None],
        "txgio:citation": NotRequired[str | None],
        "txgio:s_three_bucket_key": Required[str],
        "txgio:public": Required[bool],
        "txgio:availability": Required[bool],
        "txgio:last_modified": Required[str],
        "txgio:last_edited_by": Required[str],
        "txgio:template": Required[str],
    },
)
