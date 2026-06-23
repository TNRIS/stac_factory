# Datahub S3 Crawler

## Instructions for development
1. Change the username in the useradd line on Dockerfile to your local user.
2. put your API-CollectionID-CollectionName-Crosswalk.xlsx in the txgio_extension directory (May not be necessary for single collection generation)
3. this requires .aws keys for reading only. So add credentials for a iam user who has read access to s3. 
4. If desired setup a devcontainer


## Instructions for Dev Container Setup (Development related as well.)
1. install remote - containers plugin @ https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers
2. setup a bind type mount to desired .aws keys. I'd recommend setting the permissions to readonly for s3 for the IAM user you configure.
```
   "mounts": [
        {
            "source": "${localEnv:HOME}/.aws",
            "target": "PATH TO READONLY S3 IAM USER .aws DIRECTORY",
            "type": "bind"
        }
    ],
```
3. setup a matching username in postcreatecommand and give it permissions
    `"postCreateCommand": "useradd -ms /bin/bash EXAMPLE_USER && chown -R EXAMPLE_USER:EXAMPLE_USER /local_libs/* && chown -R EXAMPLE_USER:EXAMPLE_USER /stac_factory/*",`
4. Then set remoteuser
    `"remoteUser": "${localEnv:USER}"`
5. build dockerfile
```
    "build": {
        "dockerfile": "../Dockerfile",
        "context": "."
    },
```
6. pass in network
    `"runArgs": ["--network=host"],`
7. name docker container
    `"name": "stac_factory-devcontainer",`
8. mount workspace 
    `"workspaceMount": "source=${localWorkspaceFolder},target=/stac_factory/workspace,type=bind",`
    `"workspaceFolder": "/stac_factory/workspace",`
9. press cmd-p and type `>Dev Containers Rebuild and reopen container`
10. Subsequent starts are with > `Dev Containers Reopen in container`

## Use as a library
0. prereqs, I recommend fedora os. Make sure python, python3-devel, pdal, PDAL-devel, gdal, gdal-devel, uv, and g++ packages are installed
1. git clone https://github.com/TNRIS/stac_factory.git
2. export PYTHONPATH="/path/to/your/library:$PYTHONPATH"
3. uv pip install -e /path/to/stac_factory directory (Change to where you installed.) ((might work with uv add rather than uv pip install but I haven't tested yet. Both use uv though under the hood.))
4. from stac_factory import gen_this_stac_collection
5. from stac_factory import S3Config (Use this to configure s3 bucket)
6. When you call gen_this_stac_factory just pass in a object with api keys. and a instance of S3Config (gen_this_stac_collection(whc, s3_configuration))
7. This will upsert the collection into the postgres db in your environment
8. (Make sure you activate venv) Either using the activate script or selecting interpretor through vscode

## NOTES
1. There is no tile index for address-points or land-parcels. Skipped for now. But it can work with fallback function to generate metadata from introspection. But it takes a long time.
2. stratmap-2026-city-boundaries STATE_FIPS is 48, but tileid is 48000
3. missing tileindex for 4039 in noaa-2020-ccap-landcover-1m
4. only one tile indexed for noaa-2020-ccap-landcover-1m-r