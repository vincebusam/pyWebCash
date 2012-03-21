import sys
import aesjsonfile

sys.path.append("../")

import config

class DB(object):
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.db = aesjsonfile.load("%s/%s.json"%(config.dbdir, self.username), self.password)

    def save(self):
        aesjsonfile.dump("%s/%s.json"%(config.dbdir, self.username), self.db, self.password)

    def accountstodo(self):
        return self.db["accounts"]
