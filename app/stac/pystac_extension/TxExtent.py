from typing import Any
import pystac
from datetime import datetime

class TxExtent(pystac.Extent):
    """
    Docstring for TxExtent
    Override pystacs Extent
    """
    def __init__(
        self,
        spatial: pystac.SpatialExtent = pystac.SpatialExtent([0,0,-0,-0]),
        temporal: pystac.TemporalExtent = pystac.TemporalExtent([datetime.now(), datetime.now()]),
        extra_fields: dict[str, Any] | None = None,
    ):
        super(TxExtent, self).__init__(spatial, temporal, extra_fields)