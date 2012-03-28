#!/usr/bin/python
import os
import sys
import copy
import json
import numpy
import shutil
import base64
import string
import random
import getpass
import datetime
import StringIO
import aesjsonfile
from PIL import Image

sys.path.append("../")

import config

try:
    import prctl
    prctl.prctl(prctl.DUMPABLE, 0)
except ImportError:
    pass

def imgtrim(img):
    # This will trim any whitespace around the image
    # http://stackoverflow.com/questions/9396312/use-python-pil-or-similar-to-shrink-whitespace
    im = Image.open(StringIO.StringIO(img))
    pix = numpy.asarray(im)
    pix = pix[:,:,0:3]
    idx = numpy.where(pix-255)[0:2]
    box = map(min,idx)[::-1] + map(max,idx)[::-1]
    region = im.crop(box)
    outio = StringIO.StringIO()
    region.save(outio, "png")
    outio.seek(0)
    return outio.read()

def parse_amount(amount):
    if type(amount) == int:
        return amount
    if "." not in amount:
        amount += ".00"
    amount += "0" * (2-len(amount.split(".")[1]))
    return int(amount.replace("$","").replace(",","").replace(".",""))

def create_db(username, password):
    fn = "%s/%s.json" % (config.dbdir, username)
    if os.path.exists(fn):
        return False
    aesjsonfile.dump(fn, {}, password)
    return True

class DB(object):
    def __init__(self, username, password):
        self.username = username
        self.password = password
        fn = "%s/%s.json" % (config.dbdir, self.username)
        # Make a symlink to alias another username (e.g. email address) to account
        if os.path.islink(fn):
            self.username = os.readlink(fn).rstrip(".json")
        self.db = aesjsonfile.load("%s/%s.json" % (config.dbdir, self.username), self.password)
        self.db.setdefault("transactions",[])
        self.db.setdefault("balances",{})
        self.db.setdefault("accounts",[])

    def save(self):
        aesjsonfile.dump("%s/%s.json" % (config.dbdir, self.username), self.db, self.password)

    def backup(self):
        shutil.copyfile("%s/%s.json" % (config.dbdir, self.username),
                        "%s/%s.json-backup-%s" % (config.dbdir, self.username, str(datetime.datetime.now().replace(microsecond=0)).replace(" ","_")))

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

    def matchtrans(self, trans, query):
        for k in query:
            if k not in trans and not query[k].startswith("$ne:"):
                return False
            if not query[k].startswith("$") and query[k].lower() not in trans[k].lower():
                return False
            if query[k].startswith("$eq:"):
                if query[k].split(":")[1].lower() != str(trans[k]).lower():
                    return False
                continue
            if query[k].startswith("$ne:"):
                if query[k].split(":")[1].lower() == str(trans.get(k)).lower():
                    return False
                continue
            if query[k].startswith("$abseq:"):
                if type(trans[k]) != int or int(query[k].split(":")[1]) != abs(trans[k]):
                    return False
                continue
            if query[k].startswith("$lt:"):
                if type(trans[k]) != int or int(query[k].split(":")[1]) <= trans[k]:
                    return False
                continue
            if query[k].startswith("$gt:"):
                if type(trans[k]) == int and int(query[k].split(":")[1]) >= trans[k]:
                    return False
                continue
        return True

    def search(self, query={}, startdate="0", enddate = "9", limit=100, skip=0):
        ret = []
        for trans in self.db["transactions"]:
            if trans["date"] < startdate or trans["date"] > enddate:
                continue
            if type(query) in [ str, unicode ]:
                if query not in json.dumps(trans.values()):
                    continue
            elif query and not self.matchtrans(trans, query):
                continue
            if skip:
                skip -= 1
                continue
            ret.append(trans)
            if len(ret) >= limit:
                break
        return ret

    def getallids(self):
        return [x["id"] for x in self.db["transactions"]]

    def getimgfn(self, trans):
        return "%s/%s/%s" % (config.imgdir, self.username, trans.get("file","null"))

    def updatetransaction(self, id, new, save=True):
        for trans in self.db["transactions"]:
            if trans["id"] == id:
                trans.update(new)
                if save:
                    self.save()
                return True
        return False

    def newtransactions(self, data):
        for trans in data.get("transactions",[]):
            if trans.get("file") and data.get("files",{}).get(trans["file"]) and \
               (not os.path.exists(self.getimgfn(trans)) or trans["id"] not in self.getallids()):
                trans["filekey"] = ''.join(random.choice(string.ascii_letters + string.digits) for x in range(32))
                if not os.path.exists(os.path.dirname(self.getimgfn(trans))):
                    os.mkdir(os.path.dirname(self.getimgfn(trans)))
                img = imgtrim(base64.b64decode(data["files"][trans["file"]]))
                img = aesjsonfile.enc(img, trans["filekey"])
                open("%s/%s/%s" % (config.imgdir, self.username, trans["file"]), "w").write(img)
                if trans["id"] in self.getallids():
                    self.updatetransaction(trans["id"], {"filekey": trans["filekey"]}, False)
            if trans["id"] not in self.getallids():
                for k in [x for x in trans.keys() if not x.startswith("attr_") and x != "id"]:
                    trans["orig_"+k] = trans[k]
                trans["orig_amount_str"] = trans["amount"]
                trans["amount"] = parse_amount(trans["amount"])
                self.db["transactions"].append(trans)
                if trans.get("parent"):
                    p = self.search({"id": trans["parent"]})
                    if p:
                        self.updatetransaction(trans["parent"], {"amount": p[0]["amount"]-trans["amount"]}, False)
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

    def getimage(self, id):
        trans = self.search({"id": id})
        if trans:
            return aesjsonfile.dec(open(self.getimgfn(trans[0])).read(), trans[0]["filekey"])
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(1)
    password = getpass.getpass()
    db = DB(sys.argv[1],password)
    print "accountstodo"
    print json.dumps(db.accountstodo(), indent=2)
    print "accounts"
    print json.dumps(db.accounts(), indent=2)
    if os.getenv("DATAFILE"):
        print json.dumps(db.newtransactions(json.load(open(os.getenv("DATAFILE")))), indent=2)
    print "Last 5:"
    print json.dumps(db.search(limit=5), indent=2)
    print "Zeroed out:"
    print json.dumps(db.search(query={"amount":"$eq:0"},limit=2), indent=2)
    print "Spending:"
    print json.dumps(db.search(query={"amount":"$lt:0"},limit=2), indent=2)
    print "Income:"
    print json.dumps(db.search(query={"amount":"$gt:0"},limit=2), indent=2)
    print "Target:"
    print json.dumps(db.search(query={"desc":"$eq:Target"},limit=2), indent=2)
    print "Backup:"
    db.backup()
