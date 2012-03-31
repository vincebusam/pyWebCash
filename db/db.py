#!/usr/bin/python
import os
import re
import sys
import time
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
import aespckfile
from PIL import Image

sys.path.append("../")

import config

try:
    import prctl
    prctl.prctl(prctl.DUMPABLE, 0)
except ImportError:
    pass

parsedate = lambda x: datetime.datetime.strptime(x,"%Y-%m-%d").date()

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
    fn = "%s/%s.pck" % (config.dbdir, username)
    if os.path.exists(fn):
        return False
    aespckfile.dump(fn, {}, password)
    return True

def isopentransfer(trans):
    return trans.get("state") != "closed" and \
           not trans.get("parent") and \
           not trans.get("child") and \
           trans.get("amount") != 0 and \
           trans.get("category") == "Transfer" and \
           not "Cash" in trans.get("subcategory")

class DB(object):
    def __init__(self, username, password):
        self.username = username
        self.password = password
        fn = "%s/%s.pck" % (config.dbdir, self.username)
        # Make a symlink to alias another username (e.g. email address) to account
        if os.path.islink(fn):
            self.username = os.readlink(fn).rstrip(".pck")
        self.dbfn = "%s/%s.pck" % (config.dbdir, self.username)
        self.loaddb()
        self.lockfn = None

    def loaddb(self):
        self.dbmtime = os.path.getmtime(self.dbfn)
        self.db = aespckfile.load(self.dbfn, self.password)
        self.db.setdefault("transactions",[])
        self.db.setdefault("balances",{})
        self.db.setdefault("accounts",[])
        self.db.setdefault("centers",["home"])
        self.rules = copy.deepcopy(self.db.setdefault("rules",[]))
        self.rules.extend(json.load(open(os.path.dirname(__file__) + "/../rules.json")))

    def save(self):
        aespckfile.dump("%s/%s.pck" % (config.dbdir, self.username), self.db, self.password)
        if self.lockfn:
            os.unlink(self.lockfn)

    def backup(self):
        shutil.copyfile("%s/%s.pck" % (config.dbdir, self.username),
                        "%s/backup/%s.pck-backup-%s" % (config.dbdir, self.username, str(datetime.datetime.now().replace(microsecond=0)).replace(" ","_")))

    def getlock(self):
        if self.lockfn:
            return True
        for loop in range(10):
            try:
                fn = "%s/.%s.lck" % (config.dbdir, self.username)
                os.link(self.dbfn, fn)
                if os.path.getmtime(self.dbfn) > self.dbmtime:
                    self.loaddb()
                self.lockfn = fn
                return True
            except OSError:
                pass
            time.sleep(1)
        return False

    def accountstodo(self):
        ret = copy.deepcopy(self.db["accounts"])
        for acct in ret:
            trans = self.search({"account":acct["name"]},limit=5)
            acct["seenids"] = [x["id"] for x in trans]
            if trans:
                acct["lastcheck"] = trans[0]["date"]
        return ret

    def editaccount(self, account):
        if not self.getlock():
            return False
        curaccts = [x["name"] for x in self.db["accounts"]]
        if account["name"] in curaccts:
            self.db["accounts"][curaccts.index(account["name"])] = account
        else:
            self.db["accounts"].append(account)
        self.save()
        return True

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
        if not self.getlock():
            return False
        for trans in self.db["transactions"]:
            if trans["id"] == id:
                for k in new:
                    if k in trans:
                        trans.setdefault("orig_"+k,trans[k])
                trans.update(new)
                if save:
                    self.save()
                return True
        return False

    def newtransactions(self, data, autoprocess=True):
        if not self.getlock():
            return False
        for trans in data.get("transactions",[]):
            # Trim, encrypt, and store any images associated with the transaction
            if trans.get("file") and data.get("files",{}).get(trans["file"]) and \
               (not os.path.exists(self.getimgfn(trans)) or trans["id"] not in self.getallids()):
                trans["filekey"] = ''.join(random.choice(string.ascii_letters + string.digits) for x in range(32))
                if not os.path.exists(os.path.dirname(self.getimgfn(trans))):
                    os.mkdir(os.path.dirname(self.getimgfn(trans)))
                img = imgtrim(base64.b64decode(data["files"][trans["file"]]))
                img = aespckfile.enc(img, trans["filekey"])
                open("%s/%s/%s" % (config.imgdir, self.username, trans["file"]), "w").write(img)
                if trans["id"] in self.getallids():
                    self.updatetransaction(trans["id"], {"filekey": trans["filekey"]}, False)

            # Check if dup, then store transaction
            if trans["id"] not in self.getallids():
                trans.setdefault("state", "open")
                trans.setdefault("center", self.db["centers"][0])
                trans["orig_amount_str"] = trans["amount"]
                trans["amount"] = parse_amount(trans["amount"])
                trans["orig_amount"] = trans["amount"]
                self.db["transactions"].append(trans)
                if trans.get("parent"):
                    p = self.search({"id": trans["parent"]})
                    if p:
                        self.updatetransaction(trans["parent"], {"amount": p[0]["amount"]-trans["amount"]}, False)

        # Auto re-name, categorize, then match up transfers
        if autoprocess:
            for trans in self.db["transactions"]:
                if trans.get("autoprocessed") or trans.get("state", "open") != "open":
                    continue
                for rule in self.rules:
                    matched = True
                    for match, val in rule[0].iteritems():
                        if match == "amount" and trans["amount"] != val:
                            matched = False
                            break
                        elif match == "absamount" and abs(trans["amount"]) != val:
                            matched = False
                            break
                        elif val and not re.search(val, trans.get(match), re.I):
                            matched = False
                            break
                    if matched:
                        for k in rule[1]:
                            trans.setdefault("orig_"+k,trans[k])
                        trans.update(rule[1])
                        trans["autoprocessed"] = True
                        break
                if not trans.get("autoprocessed"):
                    # Re-capitalize desc
                    if trans["desc"].isupper() or trans["desc"].islower():
                        trans.setdefault("orig_desc",trans["desc"])
                        trans["desc"] = trans["desc"].title()
                trans["autoprocessed"] = True
            
            for i in range(len(self.db["transactions"])):
                if isopentransfer(self.db["transactions"][i]):
                    for j in range(i+1,len(self.db["transactions"])):
                        if isopentransfer(self.db["transactions"][j]) and \
                           self.db["transactions"][i]["amount"] == -self.db["transactions"][j]["amount"] and \
                           parsedate(self.db["transactions"][i]["date"]) - parsedate(self.db["transactions"][j]["date"]) <= datetime.timedelta(days=4):
                            self.db["transactions"][i]["child"] = self.db["transactions"][j]["id"]
                            self.db["transactions"][j]["parent"] = self.db["transactions"][i]["id"]
                            self.db["transactions"][i]["amount"] = 0
                            self.db["transactions"][j]["amount"] = 0

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
            return aespckfile.dec(open(self.getimgfn(trans[0])).read(), trans[0]["filekey"])
        return False

    def getcategories(self):
        cats = json.load(open(os.path.dirname(__file__) + "/../categories.json"))
        for cat in self.db.get("categories",[]):
            cats.setdefault(cat,[]).extend(self.db["categories"][cat])
        return cats

    def getcenters(self):
        return self.db["centers"]

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
    if len(sys.argv) > 2:
        print json.dumps(db.search(query=json.loads(sys.argv[2]),limit=5), indent=2)
