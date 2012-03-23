#!/usr/bin/python
import sys
import copy
import json
import getpass
import aesjsonfile

sys.path.append("../")

import config

def parse_amount(amount):
    if type(amount) == int:
        return amount
    if "." not in amount:
        amount += ".00"
    return int(amount.replace("$","").replace(",","").replace(".",""))

class DB(object):
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.db = aesjsonfile.load("%s/%s.json"%(config.dbdir, self.username), self.password)
        self.db.setdefault("transactions",[])
        self.db.setdefault("balances",{})
        self.db.setdefault("accounts",[])

    def save(self):
        aesjsonfile.dump("%s/%s.json"%(config.dbdir, self.username), self.db, self.password)

    def accountstodo(self):
        ret = copy.deepcopy(self.db["accounts"])
        for acct in ret:
            trans = self.search({"account":acct["name"]},limit=5)
            acct["seenids"] = [x["id"] for x in trans]
            if trans:
                acct["lastcheck"] = trans[0]["date"]
        return ret

    def accounts(self):
        ret = copy.deepcopy(self.db["accounts"])
        for acct in ret:
            acct.pop("password",None)
            acct["subaccounts"] = []
            for sub in self.db["balances"].get(acct["name"],{}):
                acct["subaccounts"].append({"name": sub, "amount": self.db["balances"][acct["name"]][sub][0]["amount"],
                                            "date": self.db["balances"][acct["name"]][sub][0]["lastdate"]})
        return ret

    def search(self, query={}, startdate="0", enddate = "9999", limit=100):
        ret = []
        for trans in self.db["transactions"]:
            if trans["date"] < startdate or trans["date"] > enddate:
                continue
            if type(query) in [ str, unicode ]:
                if query not in json.dumps(trans.values()):
                    continue
            elif query and type(query) == dict:
                for k in query:
                    if not trans.get(k) or query[k] not in trans[k]:
                        continue
            ret.append(trans)
            if len(trans) >= limit:
                break
        return ret

    def getallids(self):
        return [x["id"] for x in self.db["transactions"]]

    def newtransactions(self, data):
        for trans in data.get("transactions",[]):
            if trans["id"] not in self.getallids():
                self.db["transactions"].append(trans)
        self.db["transactions"].sort(cmp=lambda x,y: cmp(x["date"],y["date"]) or cmp(x["id"],y["id"]), reverse=True)
        for bal in data.get("balances",[]):
            amount = parse_amount(bal["balance"])
            oldbal = self.db["balances"].setdefault(bal["account"],{}).setdefault(bal["subaccount"],[])
            if oldbal and oldbal[0]["amount"] == amount:
                oldbal[0]["lastdate"] = bal["date"]
            else:
                oldbal.insert(0, {"amount": amount, "firstdate": bal["date"], "lastdate": bal["date"]})
        self.save()
        return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(1)
    password = getpass.getpass()
    db = DB(sys.argv[1],password)
    print "accountstodo"
    print json.dumps(db.accountstodo(),indent=2)
    print "accounts"
    print json.dumps(db.accounts(),indent=2)
