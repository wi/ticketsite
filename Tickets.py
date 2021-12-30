from datetime import datetime
from mongoDB import MongoHandler


def timestamp():
    return int(datetime.now().timestamp())


class Ticket:
    mongo = MongoHandler("tickets", "tickets")

    def __init__(self, ticket_id, ticket_owner_uid=None, message=None):
        self.ticket_id = ticket_id
        if ticket_owner_uid is None and message is None:
            self.ticket_db = self.load_ticket(ticket_id)
            if self.ticket_db is None:
                raise KeyError
            self.ticket_owner_uid = self.ticket_db['ticket_owner_uid']
        else:
            self.ticket_owner_uid = ticket_owner_uid
            self.message = message
            self.ticket_db = self.create_default_ticket()

    @classmethod
    def load_ticket(cls, ticket_id):
        return cls.mongo.get_ticket_by_id(ticket_id)

    @property
    def id(self):
        return self.ticket_db['_id']

    @property
    def ticket_owner(self):
        return self.ticket_db['ticket_owner_uid']

    @property
    def creation_date(self):
        return self.ticket_db['creation_date']

    @property
    def open(self):
        return self.ticket_db['open']

    @property
    def messages(self):
        return self.ticket_db['messages']

    @property
    def raw(self):
        return self.ticket_db

    def get_ticket_db(self):
        return self.ticket_db

    def create_default_ticket(self) -> dict:
        if self.ticket_owner_uid is not None and self.message is not None:
            self.ticket_db = {"_id": self.ticket_id, "ticket_owner_uid": self.ticket_owner_uid,
                              "creation_date": timestamp(), "open": True, "assigned": {}, "ticket_messages":
                                  {"0": {"user": self.ticket_owner_uid, "message": self.message,
                                         "timestamp": timestamp(), "edited": 0, "hidden": False}}}
            return self.ticket_db
        else:
            raise KeyError

    def add_reply(self, user_uid, message) -> None:
        if message is not None:
            temp = []
            for value in self.ticket_db['ticket_messages'].keys():
                temp.append(int(value))
            reply_num = str(max(temp) + 1)
            self.ticket_db['ticket_messages'][reply_num] = {"user": user_uid, "message": message,
                                                            "timestamp": timestamp(), "edited": 0, "hidden": False}
            if user_uid not in self.ticket_db['assigned']:
                self.ticket_db['assigned'].append(user_uid)
        else:
            return

    def edit_ticket_reply(self, message_pos, new_message) -> None:
        old_msg = self.ticket_db['ticket_messages'].get(message_pos)
        if old_msg is not None:
            self.ticket_db['ticket_messages'][message_pos]['message'] = new_message
            self.ticket_db['ticket_messages'][message_pos]['timestamp'] = timestamp()
            self.ticket_db['ticket_messages'][message_pos]['edited'] = 1
        else:
            raise KeyError

    def is_open(self):
        return self.ticket_db['open'] is True

    def close_reopen(self):
        self.ticket_db['open'] = not self.ticket_db['open']
        self.update()

    def update(self):
        self.mongo.raw_replace({'_id': self.ticket_db['_id']}, self.ticket_db)
