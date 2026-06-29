import psycopg, json

from pystac import Item
from pypgstac.load import Loader, Methods
from pypgstac.db import PgstacDB
from typing import Iterator, Optional

# Local Imports
from _internal.tx_pystac import TxOldCollection, TxNewCollection


class TxLoader(Loader):
    """
    Docstring for TxLoader
    """

    def __init__(self):
        db = PgstacDB()
        super().__init__(db)

    def delete_collection_and_items(self, collection_id) -> None:
        """
        Docstring for delete_collection
        Checks if collection then
            * deletes it if it exists
            * deletes associated items
            * all as one transaction.
            * Caveat with the above assumptions is that the db has to be in a pypgstac managed state.

        :param self: Description
        :param collection_id: Description
        """
        with psycopg.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT EXISTS (
                        SELECT 1 FROM pgstac.collections WHERE id = %s
                    );
                    """,
                    [collection_id],
                )
                row = cur.fetchone()
                exists = row and row[0]
                if exists:
                    cur.execute("SELECT pgstac.delete_collection(%s);", [collection_id])

    def get_content(self, collection_id):
        """
        Docstring for get_content
        Returns content if it exists.
        :param self: Description
        :param collection_id: Description
        """
        with psycopg.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                        SELECT content FROM pgstac.collections WHERE id = %s
                    """,
                    [collection_id],
                )
                row = cur.fetchone()
                exists = row and row[0]
                if exists:
                    return row[0]

    def load_collection_and_items(
        self,
        file: TxOldCollection | TxNewCollection,
        dict_items: Iterator[Item],
        insert_mode: Optional[Methods] = Methods.upsert,
    ) -> None:
        if insert_mode == Methods.upsert:
            self.delete_collection_and_items(file.collection_name)
            insert_mode = Methods.insert
        self.get_content(file.collection_name)

        # Load Collections
        collections = iter([json.dumps(file.to_dict())])
        super().load_collections(collections, insert_mode)

        # Load Items
        items = []
        for i in dict_items:
            items.append(i.to_dict())
        super().load_items(iter(items))
