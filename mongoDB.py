import pymongo


class MongoHandler:
    def __init__(self, database: str, collection: str = None):
        self.db = pymongo.MongoClient("URL")
        self.db = self.db[f'{database}']
        if collection is not None:
            self.db = self.db[f'{collection}']

    def raw_query(self, query, collection=None, one=True):
        if collection is not None:
            return self.db[f'{collection}'].find_one(query) if one is True else self.db[f'{collection}'].find(query)
        return self.db.find_one(query) if one is True else self.db.find(query)

    def raw_insert(self, data, collection=None):
        self.db[f'{collection}'].insert_one(data) if collection is not None else self.db.insert_one(data)

    def raw_update(self, query, data, collection=None):
        self.db[f'{collection}'].update_one(query, data) if collection is not None else self.db.update_one(query, data)

    def raw_replace(self, query, data, collection=None):
        self.db[f'{collection}'].replace_one(query, data) if collection is not None else self.db.replace_one(query, data)

    def get_ticket_by_id(self, ticket_id):
        return self.db.find_one({"_id": ticket_id})

    def get_max_value(self, sort_by: str, collection=None) -> dict:
        if collection is None:
            num = self.db.find_one(sort=[(sort_by, -1)])
            return num if num is not None else {'_id': 1}
        num = self.db[f'{collection}'].find_one(sort=[(sort_by, -1)])
        return num if num is not None else {'_id': 1}



