#!/usr/bin/python
import sys
import copy
import json
import getpass
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

    def accounts(self):
        ret = copy.deepcopy(self.db["accounts"])
        for acct in ret:
            acct.pop("password",None)
        return ret

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(1)
    password = getpass.getpass()
    db = DB(sys.argv[1],password)
    print "accountstodo"
    print json.dumps(db.accountstodo(),indent=2)
    print "accounts"
    print json.dumps(db.accounts(),indent=2)
