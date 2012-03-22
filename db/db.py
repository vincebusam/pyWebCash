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
        for a in self.db.get("balances",{}):
            for s in self.db["balances"][a]:
                self.db["balances"][a][s].sort(key=lambda x: x["lastdate"], reverse=True)
        if self.db.get("transactions"):
            self.db.transactions.sort(key=lambda x: x["id"], reverse=True)
        aesjsonfile.dump("%s/%s.json"%(config.dbdir, self.username), self.db, self.password)

    def accountstodo(self):
        ret = copy.deepcopy(self.db["accounts"])
        for acct in ret:
            acct["seenids"] = []
            for trans in self.db.get("transactions",[]):
                if trans["account"] == acct["name"]:
                    acct["lastcheck"] = trans["date"]
                    acct["seenids"].append(trans["id"])
                    if len(acct["seenids"]) >= 10:
                        break
        return ret

    def accounts(self):
        ret = copy.deepcopy(self.db["accounts"])
        for acct in ret:
            acct.pop("password",None)
            acct["subaccounts"] = []
            for sub in self.db.get("balances",{}).get(acct["name"],{}):
                acct["subaccounts"].append({"name": sub, "amount": self.db["balances"][acct["name"]][sub][0]["amount"],
                                            "date": self.db["balances"][acct["name"]][sub][0]["lastdate"]})
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
