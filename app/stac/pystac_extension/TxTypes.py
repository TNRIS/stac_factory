from multiprocessing import Process
import shapely, json

from geopandas import GeoDataFrame
from shapely.geometry.base import BaseGeometry
from app.stac import log_exception

class TileIndex():
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
            union = panda_layer.union_all(grid_size= 0.0001) # Create a grid of ~100M, just to get a practical file size.
            self.simplify = union.simplify(tolerance=0.0001, preserve_topology=True) #Defaults to Douglas Peucker, recommended in api for the_geom.
            self.outline = json.loads(shapely.to_geojson(self.simplify, indent=0))
            self.dict = panda_layer.to_dict()
        except Exception as e:
            log_exception(e)

