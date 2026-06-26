import pystac
import pystac.stac_object


def itemReader(path: str) -> pystac.Item:
    item: pystac.STACObject = pystac.read_file(path)
