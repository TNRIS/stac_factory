from pathlib import Path

ROOT = Path(__file__).resolve().parents[0]
CONFIG = ROOT / "config"
COUNTY_BOUNDARIES = CONFIG / "county_boundaries.geojson"
CITY_BOUNDARIES = CONFIG / "TX_Cities.json"
CROSS_WALK = CONFIG / "API-CollectionID-CollectionName-Crosswalk.xlsx"
CATALOG_ROOT = ROOT / "catalog" # Don't change this unless you know what it does.
TEST_GEOJSON_ROOT = ROOT / "testgeojson"