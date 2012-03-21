import sys
import aesjsonfile

sys.path.append("../")

import config

class DB(object):
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.db = aesjsonfile.load("%s/%s.json"%(config.dbdir,username), password)

    def save():
        aesjsonfile.dump("%s/%s.json"%(config.dbdir,username), self.db, password)
