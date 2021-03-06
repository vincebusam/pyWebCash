#!/usr/bin/python
# Main database.  Stores all transactions, accounts, user-specific configuration
import os
import re
import sys
import time
import copy
import numpy
import shutil
import base64
import string
import random
import locale
import getpass
import datetime
import StringIO
import aespckfile
from PIL import Image
try:
    import simplejson as json
except:
    import json

sys.path.append((os.path.dirname(__file__) or ".") + "/../")

import config

try:
    import prctl
    prctl.prctl(prctl.DUMPABLE, 0)
except ImportError:
    pass

locale.setlocale(locale.LC_ALL, '')

parsedate = lambda x: datetime.datetime.strptime(x,"%Y-%m-%d").date()
prettyformat = lambda x: locale.currency(float(x)/100, grouping=True)

digitre = re.compile("^#?\d{2,}$")

def imgtrim(img):
    """This will trim any whitespace around the image
    http://stackoverflow.com/questions/9396312/use-python-pil-or-similar-to-shrink-whitespace"""
    im = Image.open(StringIO.StringIO(img))
    pix = numpy.asarray(im)
    pix = pix[:,:,0:3]
    idx = numpy.where(pix-255)[0:2]
    try:
        box = map(min,idx)[::-1] + map(max,idx)[::-1]
        region = im.crop(box)
    except ValueError:
        region = im
    outio = StringIO.StringIO()
    region.save(outio, "png")
    outio.seek(0)
    return outio.read()

def parse_amount(amount):
    """Convert string dollar amount into cents."""
    if type(amount) == int:
        return amount
    if "." not in amount:
        amount += ".00"
    amount += "0" * (2-len(amount.split(".")[1]))
    return int(amount.replace("$","").replace(",","").replace(".","").replace("USD",""))

def create_db(username, password):
    """Make a new database"""
    fn = "%s/%s.pck" % (config.dbdir, username)
    if os.path.exists(fn):
        return False
    aespckfile.dump(fn, {}, password)
    newdb = DB(username, password)
    newdb.save()
    return True

def isopentransfer(trans):
    """All of these must pass to see if this can be matched with another transfer"""
    return trans.get("state") != "closed" and \
           not trans.get("parents") and \
           not trans.get("children") and \
           trans.get("amount") != 0 and \
           trans.get("category") == "Transfer" and \
           not "Cash" in trans.get("subcategory","")

class DB(object):
    def __init__(self, username, password):
        self.lockfn = None
        self.username = username
        self.password = password
        fn = "%s/%s.pck" % (config.dbdir, self.username)
        # Make a symlink to alias another username (e.g. email address) to account
        if os.path.islink(fn):
            self.username = os.readlink(fn).rstrip(".pck")
        self.dbfn = "%s/%s.pck" % (config.dbdir, self.username)
        self.loaddb()

    def __del__(self):
        if self.lockfn:
            os.unlink(self.lockfn)

    def loaddb(self):
        self.dbmtime = os.path.getmtime(self.dbfn)
        self.db = aespckfile.load(self.dbfn, self.password)
        self.db.setdefault("transactions",[])
        self.db.setdefault("balances",{})
        self.db.setdefault("accounts",[])
        self.db.setdefault("centers",["home"])
        self.db.setdefault("rules",[])
        self.db.setdefault("cities",[])
        self.db.setdefault("states",["CA"])
        self.db.setdefault("categories",{})
        self.db.setdefault("tags",[])
        self.rules = copy.deepcopy(self.db.setdefault("rules",[]))
        self.rules.extend(json.load(open((os.path.dirname(__file__) or ".") + "/../rules.json")))
        self.citymatch = re.compile(" (%s) ?(%s)?$" % ("|".join(self.db["cities"]), "|".join(self.db["states"])), re.I)

    def save(self):
        aespckfile.dump(self.dbfn, self.db, self.password)
        if self.lockfn:
            os.unlink(self.lockfn)
            self.lockfn = None
            self.dbmtime = os.path.getmtime(self.dbfn)

    def backup(self):
        shutil.copyfile("%s/%s.pck" % (config.dbdir, self.username),
                        "%s/backup/%s.pck-backup-%s" % (config.dbdir, self.username, str(datetime.datetime.now().replace(microsecond=0)).replace(" ","_")))
        [os.unlink("%s/backup/%s" % (config.dbdir,y)) for y in [x for x in sorted(os.listdir("%s/backup" % (config.dbdir)), reverse=True) if x.startswith(self.username + ".pck-backup")][20:]]

    def clear(self):
        """Wipes out all account history!!!"""
        self.db["transactions"] = []
        self.db["balances"] = {}

    def getlock(self):
        """Use a hard-link as a lock.  Re-load database file if mtime has changed since load"""
        if self.lockfn:
            return True
        fn = "%s/.%s.lck" % (config.dbdir, self.username)
        for loop in range(10):
            try:
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
        """Return list of accounts that need new data"""
        ret = copy.deepcopy(self.db["accounts"])
        for acct in ret:
            trans = self.search({"account":acct.get("name")},limit=20)
            acct["seenids"] = [x["id"] for x in trans]
            if trans:
                acct["lastcheck"] = trans[0]["date"]
            for sub in self.db["balances"].get(acct["name"],{}):
                if self.db["balances"][acct["name"]][sub][0]["lastdate"] > acct.get("lastcheck"):
                    acct["lastcheck"] = self.db["balances"][acct["name"]][sub][0]["lastdate"]
        return [x for x in ret if x.get("lastcheck") < str(datetime.date.today()) ]

    def editaccount(self, account):
        """Create or edit an account"""
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
        """List of accounts, subaccounts with balances, don't need passwords here"""
        ret = copy.deepcopy(self.db["accounts"])
        for acct in ret:
            acct.pop("password",None)
            acct["subaccounts"] = []
            for sub in self.db["balances"].get(acct["name"],{}):
                acct["subaccounts"].append({"name": sub, "amount": self.db["balances"][acct["name"]][sub][0]["amount"],
                                            "date": self.db["balances"][acct["name"]][sub][0]["lastdate"]})
        return ret

    def matchtrans(self, trans, query):
        """Query function"""
        for k in query:
            if k == "all":
                if not [x for x in trans.values() if query[k].lower() in unicode(x).lower()]:
                    return False
                continue
            if (k not in trans or not trans[k]) and type(query[k]) in [ str, unicode ] and query[k].lower() in [ "uncategorized", "none" ]:
                continue
            if k not in trans and not query[k].startswith("$ne:"):
                return False
            if not query[k].startswith("$") and query[k].lower() not in unicode(trans[k]).lower():
                return False
            if query[k].startswith("$eq:"):
                if query[k].split(":")[1].lower() != unicode(trans[k]).lower():
                    return False
                continue
            if query[k].startswith("$ne:"):
                if query[k].split(":")[1].lower() == unicode(trans.get(k)).lower():
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
            if query[k].startswith("$abslt:"):
                if type(trans[k]) != int or int(query[k].split(":")[1]) < abs(trans[k]):
                    return False
                continue
            if query[k].startswith("$gt:"):
                if type(trans[k]) == int and int(query[k].split(":")[1]) >= trans[k]:
                    return False
                continue
            if query[k].startswith("$absgt:"):
                if type(trans[k]) == int and int(query[k].split(":")[1]) > abs(trans[k]):
                    return False
                continue
        return True

    def search(self, query={}, startdate="0", enddate = "9", limit=100, skip=0, sort=None):
        ret = []
        if sort:
            alltrans = copy.deepcopy(self.db["transactions"])
            if sort == "absamount":
                alltrans.sort(key = lambda x: abs(x.get("amount",0)), reverse=True)
        else:
            alltrans = self.db["transactions"]
        for trans in alltrans:
            if trans["date"] < startdate or trans["date"] > enddate:
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

    sumval = {
        "month": lambda x: x["date"][:7],
        "year": lambda x: x["date"][:4]
    }
    
    modifyfunc = {
        "center": lambda trans, filter: trans.update({"center": filter.get("center"), "category": trans["center"]}) if trans["center"] != filter.get("center") else None
    }

    def summary(self, startdate=str((datetime.date.today().replace(day=1)-datetime.timedelta(days=1)).replace(day=1)),
                      enddate=str(datetime.date.today().replace(day=1)-datetime.timedelta(days=1)),
                      filter={},
                      filterout={},
                      key="category",
                      keydef="Uncategorized",
                      keysort="amount",
                      keysortrev=True,
                      subkey="subcategory",
                      subkeydef="",
                      subkeysort="amount",
                      subkeysortrev=True,
                      modify=None):
        """Summarize transactions for a report (& chart)
           params:
             startdate, enddate - date range
             filter, filter out - filters to match (or remove) transactions
             key - transaction key to aggregate on, with keydef as the default
             subkey, subkeydef - aggregate on under key
        """
        ret = {}
        suminfo = {"startdate": startdate, "enddate": enddate, "filter": filter, "filterout": filterout, "key": [key, subkey]}
        count = 0
        for trans in self.db["transactions"]:
            trans = copy.deepcopy(trans)
            if modify:
                self.modifyfunc[modify](trans, filter)
            if trans["date"] > enddate:
                continue
            if trans["date"] < startdate:
                continue
            if filter and not self.matchtrans(trans, filter):
                continue
            if filterout and self.matchtrans(trans, filterout):
                continue
            count += 1
            if key in self.sumval:
                keyval = self.sumval[key](trans)
            else:
                keyval = trans.get(key, keydef) or keydef
            if subkey in self.sumval:
                subkeyval = self.sumval[subkey](trans)
            else:
                subkeyval = trans.get(subkey, subkeydef) or subkeydef
            ret.setdefault(keyval,{"amount":0})["amount"] += trans["amount"]
            if subkey:
                ret[keyval].setdefault("subs",{}).setdefault(subkeyval,{"amount":0})["amount"] += trans["amount"]
        suminfo["totalcount"] = count
        [ret.pop(x) for x in ret.keys() if ret[x]["amount"] == 0]
        [ret[x].update(suminfo) for x in ret.keys()]
        [[ret[x]["subs"].pop(y) for y in ret[x]["subs"].keys() if ret[x]["subs"][y]["amount"] == 0] for x in ret.keys()]
        for k,v in ret.iteritems():
            v.update({"name":k})
            for sk, sv in v["subs"].iteritems():
                sv.update({"name":sk})
            v["subs"] = sorted(v["subs"].values(), key=lambda x: x[subkeysort], reverse=subkeysortrev)
        return sorted(ret.values(), key=lambda x: x[keysort], reverse=keysortrev)

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
            if trans["id"] in self.getallids():
                continue
            trans.setdefault("state", "open")
            trans.setdefault("center", ([x for x in self.db["accounts"] if x["name"] == trans.get("account")] or [{}])[0].get("center") or self.db["centers"][0])
            trans.setdefault("orig_amount_str", trans["amount"])
            trans["amount"] = parse_amount(trans["amount"])
            trans["orig_amount"] = trans["amount"]
            if trans.get("parents"):
                p = self.search({"id": "$eq:"+trans["parents"][0]})
                for t in p:
                    self.updatetransaction(trans["parents"][0], {"amount": t["amount"]-trans["amount"]}, False)

            # Auto re-name, categorize, then match up transfers
            if autoprocess:
                if trans.get("autoprocessed") or trans.get("state", "open") != "open":
                    continue
                # Go through all rename/edit rules
                for rule in self.rules:
                    matched = True
                    for match, val in rule[0].iteritems():
                        if match == "amount" and trans["amount"] != val:
                            matched = False
                            break
                        elif match == "absamount" and abs(trans["amount"]) != val:
                            matched = False
                            break
                        elif val and not re.search(unicode(val), unicode(trans.get(match,"")), re.I):
                            matched = False
                            break
                    if matched:
                        for k in rule[1]:
                            if k in trans:
                                trans.setdefault("orig_"+k,trans[k])
                        trans.update(rule[1])
                        trans["autoprocessed"] = True
                        break
                # Re-capitalize desc
                if trans["desc"].isupper() or trans["desc"].islower():
                    trans.setdefault("orig_desc", trans["desc"])
                    trans["desc"] = " ".join([x[0].upper()+x[1:] if len(x) > 2 else x.upper() for x in trans["desc"].lower().split() if not digitre.match(x)])
                # Remove any local cities from the descriptions
                trans["desc"] = self.citymatch.sub("", trans["desc"])
                trans["autoprocessed"] = True
                
                # See if we can match this transfer with another, and cancel them out.
                if isopentransfer(trans):
                    for target in self.db["transactions"]:
                        if isopentransfer(target) and \
                           trans["amount"] == -target["amount"] and \
                           parsedate(trans["date"]) - parsedate(target["date"]) <= datetime.timedelta(days=4):
                            trans.setdefault("children",[]).append(target["id"])
                            target["parents"] = [trans["id"]]
                            trans["amount"] = 0
                            target["amount"] = 0
                            break
                # For a cash transaction, split it out of most recent ATM withdrawl.
                if trans["account"].lower() == "cash" and \
                   trans["state"] == "open" and \
                   not trans.get("parents"):
                    for target in self.db["transactions"]:
                        if target.get("subcategory") == "Cash & ATM" and \
                           target["amount"] < trans["amount"] and \
                           target["date"] <= trans["date"]:
                            target["amount"] -= trans["amount"]
                            trans["parents"] = [target["id"]]
                            target.setdefault("children",[]).append(trans["id"])
                            break

            self.db["transactions"].insert(0,trans)

        # Sort for fastest performance on default (most recent) searches
        self.db["transactions"].sort(cmp=lambda x,y: cmp(x["date"],y["date"]) or cmp(x["id"],y["id"]), reverse=True)

        # Update balances
        for bal in data.get("balances",[]):
            amount = parse_amount(bal["balance"])
            oldbal = self.db["balances"].setdefault(bal["account"],{}).setdefault(bal["subaccount"],[])
            if oldbal and oldbal[0]["amount"] == amount:
                oldbal[0]["lastdate"] = bal["date"]
            else:
                oldbal.insert(0, {"amount": amount, "firstdate": bal["date"], "lastdate": bal["date"]})
        self.save()

        return True

    def link(self, parent, children, type, save=True):
        # Make sure we can find parent and children
        parenttrans = (self.search({"id": "$eq:"+parent}) or [{}])[0]
        if not parenttrans:
            return False
        childtrans = [(self.search({"id": "$eq:"+x}) or [{}])[0] for x in children]
        if [x for x in childtrans if not x]:
            return False
        parenttrans.setdefault("children", []).extend(children)
        [x.setdefault("parents",[]).append(parent) for x in childtrans]
        if type == "dup":
            [x.update({"amount": 0}) for x in childtrans]
        elif type == "combine":
            for child in childtrans:
                parenttrans["amount"] += child["amount"]
                child["amount"] = 0
        elif type == "split":
            parenttrans["amount"] -= sum([x.get("amount") for x in childtrans])
        self.getlock()
        if save:
            self.save()
        return True

    def unlink(self, parentid, childid, type, save=True):
        parent = (self.search({"id": "$eq:"+parentid}) or [{}])[0]
        if not parent or childid not in parent.get("children",[]):
            return False
        child = (self.search({"id": "$eq:"+childid}) or [{}])[0]
        if not child or parentid not in child.get("parents",[]):
            return False
        parent["children"].remove(childid)
        child["parents"].remove(parentid)
        if type == "dup":
            child["amount"] = child["orig_amount"]
        elif type == "combine":
            child["amount"] = child["orig_amount"]
            parent["amount"] -= child["amount"]
        elif type == "split":
            parent["amount"] += child["amount"]
        if save:
            self.save()
        return True

    def getimage(self, id):
        trans = self.search({"id": "$eq:"+id})
        if trans:
            return aespckfile.dec(open(self.getimgfn(trans[0])).read(), trans[0]["filekey"])
        return False

    def getcategories(self):
        cats = json.load(open((os.path.dirname(__file__) or ".") + "/../categories.json"))
        for cat in self.db.get("categories",{}):
            cats.setdefault(cat,[]).extend(self.db["categories"][cat])
        return cats

    def getcenters(self):
        return self.db["centers"]

    def gettags(self):
        return self.db["tags"]

    def getquestions(self):
        return self.db.get("questions", {})

    def balancehistory(self):
        ret = []
        for acct in self.db["balances"]:
            for subacct in self.db["balances"][acct]:
                data = [(int(time.mktime(parsedate(b["lastdate"]).timetuple()))*1000, b["amount"]) for b in self.db["balances"][acct][subacct]]
                data.append(((int(time.mktime(parsedate(self.db["balances"][acct][subacct][-1]["firstdate"]).timetuple())))*1000, self.db["balances"][acct][subacct][-1]["amount"]))
                data.reverse()
                ret.append({"name": "%s/%s" % (acct, subacct),
                            "data": data})
        return ret

    def getcookies(self):
        return self.db.get("cookies", [])

    def setcookies(self, cookies, save=True):
        self.db["cookies"] = cookies
        if save:
            self.save()
        return True

if __name__ == "__main__":
    import readline, fcntl, termios, struct
    try:
        readline.read_history_file(os.path.join(os.path.expanduser("~"), ".pywebcash"))
    except IOError:
        pass
    if len(sys.argv) < 2:
        sys.exit(1)
    while True:
        try:
            password = getpass.getpass()
            if not password:
                sys.exit(0)
            db = DB(sys.argv[1],password)
            break
        except Exception, e:
            print e
            print "Invalid Password"
    # Pop off non-commands from argv
    sys.argv.pop(0)
    sys.argv.pop(0)
    results = []
    year = ""
    searchquery = {}
    while True:
        if len(sys.argv):
            arg = sys.argv.pop(0)
            if not arg.strip():
                break
        else:
            try:
                arg = raw_input("> ").strip()
            except EOFError:
                print
                readline.write_history_file(os.path.join(os.path.expanduser("~"), ".pywebcash"))
                break
        if not arg:
            continue
        if os.path.exists(arg):
            print "Data import:"
            print json.dumps(db.newtransactions(json.load(open(arg))), indent=2)
        elif arg == "clear":
            print "Clear database"
            db.clear()
            db.save()
        elif arg == "todo":
            print "Accounts TODO:"
            accounts = db.accountstodo()
            for acct in accounts:
                print "  %s %s" % (acct["name"], acct.get("username"))
        elif arg == "balances":
            print "Accounts:"
            accounts = db.accounts()
            for acct in accounts:
                print "  %s %s" % (acct["name"], acct.get("username"))
                for sub in acct.get("subaccounts",[]):
                    print "    %s %s" % (sub["name"], prettyformat(sub["amount"]))
        elif arg == "summary":
            print json.dumps(db.summary(), indent=2)
        elif arg == "balancehistory":
            print json.dumps(db.balancehistory(), indent=2)
        elif arg.isdigit():
            if len(results) >= int(arg):
                res = results[int(arg)-1]
                mainkeys = ["date", "account", "subaccount", "desc", "orig_desc", "amount", "category", "subcategory"]
                for key in mainkeys:
                    print "%s: %s" % (key, res.get(key) if key != "amount" else prettyformat(res["amount"]))
                for key in res.keys():
                    if key not in mainkeys:
                        print "%s: %s" % (key, res[key])
        elif arg.startswith("update"):
            update = json.loads(arg.split(None,1)[1])
            print "Update loaded transactions with %s" % (update)
            for t in results:
                db.updatetransaction(t["id"], update, save=False)
            db.save()
        elif arg.startswith("split"):
            if len(results) != 1:
                print "Narrow search to 1 result"
                continue
            newtrans = copy.deepcopy(results[0])
            for newid in range(10):
                if "%s-%s" % (newtrans["id"],newid) not in results[0].get("children",[]):
                    newtrans["id"] += "-%s" % (newid)
                    break
            newtrans.pop("children", None)
            newtrans.pop("parents", None)
            newtrans["amount"] = int(arg.split()[1])
            newtrans["parents"] = [ results[0]["id"] ]
            results[0].setdefault("children", []).append(newtrans["id"])
            db.newtransactions({"transactions": [newtrans]}, autoprocess=False)
        elif arg.startswith("year"):
            year = arg[len("year "):]
            print "Year %s set" % (year)
        elif arg.startswith("search"):
            if "clear" in arg:
                searchquery = {}
            else:
                try:
                    searchquery.update(json.loads(arg[len("search "):]))
                except Exception, e:
                    print e
                    continue
            try:
                results = db.search(query=searchquery,startdate=year+"-01-01" if year else "0",enddate=year+"-12-31" if year else "9",limit=sys.maxint)
            except Exception, e:
                print e
                continue
            print "%s transactions" % (len(results))
        elif arg.startswith("csv"):
            f = None
            if len(arg) > len("csv "):
                f = open(arg[len("csv "):], "w")
            header = "Id,Date,Description,Orig Desc,Bank,Account,Amount,Category,Subcategory"
            print header
            if f:
                f.write(header + "\n")
            csvescape = lambda s: "\"" + s.replace("\"","\"\"") + "\"" if "\"" in s or "," in s else s
            for res in results:
                line = ",".join([csvescape(res[x]) if type(res.setdefault(x,"")) in [ str, unicode ] else csvescape(prettyformat(res[x])) for x in ["id", "date", "desc", "orig_desc", "account", "subaccount", "amount", "category", "subcategory"]])
                print line
                if f:
                    f.write(line + "\n")
            if f:
                f.close()
        elif arg.startswith("{"):
            print "Query for %s" % (arg)
            try:
                results = db.search(query=json.loads(arg),limit=sys.maxint)
            except Exception, e:
                print e
                continue
            h, w, hp, wp = struct.unpack('HHHH',fcntl.ioctl(0, termios.TIOCGWINSZ,struct.pack('HHHH', 0, 0, 0, 0)))
            descwidth = w - 35
            for res in results:
                print ("{0} {1:10} {2:%s} {3:>12}" % (descwidth)).format(res["date"], (res.get("subaccount") or res["account"])[:10], res["desc"][:descwidth].encode("ascii","ignore"), prettyformat(res["amount"]))
            print "%s Transactions, Total %s" % (len(results), prettyformat(sum([x["amount"] for x in results])))
        elif arg.startswith("missing"):
            accounts = db.accounts()
            for acct in accounts:
                for sub in acct["subaccounts"]:
                    try:
                        results = db.search(query={"subaccount": sub["name"], "account": acct["name"]}, startdate=str(datetime.date(datetime.date.today().year-1,1,1)), limit=sys.maxint)
                        if len(results) < 100:
                            continue
                        print "%s/%s: %s transactions" % (acct["name"], sub["name"], len(results))
                        olddate = datetime.datetime.strptime(results[0]["date"],"%Y-%m-%d").date()
                        for d in results:
                            newdate = datetime.datetime.strptime(d["date"],"%Y-%m-%d").date()
                            if abs(newdate-olddate) > datetime.timedelta(days=5):
                                print "No transactions %s -> %s" % (newdate,olddate)
                            olddate = newdate
                    except Exception, e:
                        print e
        elif arg.startswith("unlink"):
            if not results or len(results[0].get("parents",[])) != 1:
                print "Not unlinkable"
                continue
            type = arg[len("unlink "):]
            if not type:
                print "Type needed"
                continue
            if not db.unlink(results[0]["parents"][0],results[0]["id"],type,False):
                print "Unlink failed"
        elif arg.startswith("tagyear"):
            tags = {}
            lastyear = arg[len("tagyear "):] or str(datetime.datetime.today().year-1)
            for t in db.search(startdate=lastyear+"-01-01",enddate=lastyear+"-12-31",limit=sys.maxint):
                for tag in t.get("tags",[]):
                    tags.setdefault(tag,0)
                    tags[tag] += t["amount"]
            for tag in tags:
                print "%s: %s" % (tag, prettyformat(tags[tag]))
        elif arg.startswith("1099exp"):
            # This helps find expenses that were reimbursed, but counted as income on a 1099.
            cats = {}
            lastyear = str(datetime.datetime.today().year-1)
            for t in db.search(query={"amount":"$gt:0","desc":arg[8:]},startdate=lastyear+"-01-01",enddate=lastyear+"-12-31",limit=sys.maxint):
                for child in t.get("children",[]):
                    subt = db.search({"id":child})[0]
                    sumcat = subt["subcategory"] or subt["category"]
                    cats.setdefault(sumcat,0)
                    cats[sumcat] += subt["orig_amount"]
            for cat in cats:
                print "%s %s" % (cat, prettyformat(cats[cat]))
        elif arg.startswith("save"):
            db.save()
        else:
            print "Unknown command %s" % (arg)
