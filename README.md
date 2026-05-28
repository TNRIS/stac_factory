# Datahub S3 Crawler
1. Create a config.py from config_example.py with test and prod s3 buckets. (I can send a configured file to TWDB employees)
2. Change the username in the useradd line on Dockerfile to your local user. (Currently lh)
3. create a config_db.sh with your postgresql db. (config_db_example.sh can be used as a base)
4. put your API-CollectionID-CollectionName-Crosswalk.xlsx in the txgio_extension directory
## Dev Container Setup
1. install remote - containers plugin @ https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers
2. press cmd-p and type `>Dev Containers Reopen Folder Locally`

## Test DB Setup.
Create a local django db (follow the instructions in api.tnris.org repo) and copy the config_db_example.sh file and name is config_db.sh and input your local db credentials.
If you want to use our real db then add tunnel.sh and run it. then configure config_db.sh

## Use as a library
1. git clone https://github.com/TNRIS/stac_factory.git
2. import gen_this_stac_collection from path to stac_factory
3. When you call gen_this_stac_factory just pass in name of s3 key
4. This will upsert the collection into the postgres db in your environment

TODO:
1. There is no way to reference naip-2016-nc-cir-1m/,  it only has a USGISID and that's not the id in the directory structure. None of the tiles match up to the index there, neither do any of the file names there. I'm not sure hat's going on there. I think that ones messed up.
 
All the tile indexes should have a common name for the indexes. Like TileID or something. So far it's inconsistent.
 
Ryan said he'd fix it later so it might be a wip. I'll skip over the 016 naip for now

2. There is no tile index for address-points or land-parcels. Skipped for now. But it can work with fallback function to generate metadata from introspection. But it takes a long time.

3. I haven't reduced the txgio:schema fields yet, I haven't added the two extensions yet. I didn't want to rush it. 

4. I generated 1 and a half collections without issues. The dallas-pecos one was taking a long time. Just the shear amount of files take a while. Might be faster to wait until the collection is totally complete to save the stac to disk. I'll try that when I get back.

NOTE: API-CollectionID-CollectionName-Crosswalk.html is a plain html file. Load as Doc Object Model to parse. It's a standard LibreOffice Document Object Model export of Ryans xlsx file. I chose to use this since I don't need any external libraries.
