# Datahub S3 Crawler

## Instructions for development
1. Change the username in the useradd line on Dockerfile to your local user. (Currently lh)
2. create a config_db.sh with your postgresql db. (config_db_example.sh can be used as a base)
3. put your API-CollectionID-CollectionName-Crosswalk.xlsx in the txgio_extension directory (May not be necessary for single collection generation)

## Instructions for Dev Container Setup (Development related as well.)
1. install remote - containers plugin @ https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers
2. press cmd-p and type `>Dev Containers Reopen Folder Locally`

## Use as a library
0. prereqs, I recommend fedora os. Make sure python, python3-devel, pdal, PDAL-devel, gdal, gdal-devel, uv, and g++ packages are installed
1. git clone https://github.com/TNRIS/stac_factory.git
2. export PYTHONPATH="/path/to/your/library:$PYTHONPATH"
3. uv pip install -e /path/to/stac_factory directory (Change to where you installed.) ((might work with uv add rather than uv pip install but I haven't tested yet. Both use uv though under the hood.))
4. import S3Config class and use that to configure s3 bucket.
5. import gen_this_stac_collection from path to stac_factory
6. When you call gen_this_stac_factory just pass in a object with api keys. and a instance of S3Config (gen_this_stac_collection(whc, s3_configuration))
7. This will upsert the collection into the postgres db in your environment
8. (Make sure you activate venv) Either using the activate script or selecting interpretor through vscode

## NOTES
1. There is no tile index for address-points or land-parcels. Skipped for now. But it can work with fallback function to generate metadata from introspection. But it takes a long time.
