#!/usr/bin/python
# Scraper template
import re
import api
import sys
import time
import json
import rfc822
import quopri
import common
import hashlib
import getpass
import imaplib
import StringIO
import datetime

def uploaditems(parent, items):
    [x.update({"parent": parent}) for x in items]
    api.callapi("newtransactions", {"data": json.dumps({"transactions": items}, default=str)})
    api.callapi("updatetransaction", {"id": parent, "data": json.dumps({"amount":0, "children": [x["id"] for x in items]})})

def checkitems(items, amazontrans, amount, itemsamount, params):
    if items[0]["id"] in params["seenids"]:
        return
    if "%s-%s-Amazon-%s" % (items[0]["date"], params["name"], hashlib.sha1(str(items[0]["quantity"]) + ' "' + items[0]["desc"]).hexdigest()+'"') in params["seenids"]:
        return
    if sum([x["amount"] for x in items]) != amount:
        if sum([x["amount"] for x in items]) == itemsamount:
            # Distribute tax/shipping/discounts evenly among items for now
            diff = amount - itemsamount
            for item in items:
                item["amount"] += diff/len(items)
        else:
            print "Item amount / total mismatch! %s %s" % (items[0]["date"], amount)
            return
    print "Finding a match for %s %s" % (items[0]["date"], amount)
    trans = [x for x in amazontrans if x["amount"] == amount]
    if trans:
        print "Matched to %s" % (trans[0]["id"])
        uploaditems(trans[0]["id"], items)
    else:
        for item in items:
            trans = [x for x in amazontrans if x["amount"] == item["amount"]]
            if trans:
                print "Matched to %s" % (trans[0]["id"])
                uploaditems(trans[0]["id"], [item])
            else:
                print "No match found"

def downloadaccount(b, params):
    if "password" not in params:
        params["password"] = getpass.getpass("IMAP Password for %s at %s: " % (params["username"], params["server"]))
    params.setdefault("name", "Email")
    params.setdefault("mailbox", "INBOX")
    params.setdefault("seenids",[])
    params.setdefault("lastcheck",datetime.date(2000,1,1))
    if type(params["lastcheck"]) in [ str, unicode ]:
        params["lastcheck"] = common.parsedate(params["lastcheck"])
    params["lastcheck"] -= datetime.timedelta(days=4)

    imap = imaplib.IMAP4_SSL(params["server"])
    imap.login(params["username"],params["password"])
    imap.select(params["mailbox"])

    amazontrans = api.callapi("search",{"query": json.dumps({"desc": "amazon", "amount": "$ne:0"})})
    msgs = sorted(map(int,imap.search(None, "FROM", "auto-confirm@amazon.com")[1][0].split()),reverse=True)
    for msg in msgs:
        initems = False
        item = {}
        items = []
        out = StringIO.StringIO()
        messagetext = quopri.decode(StringIO.StringIO(imap.fetch(str(msg), "(RFC822)")[1][0][1]), out)
        out.seek(0)
        for line in out.read().split("\n"):
            line = line.strip()
            if line.startswith("Date:"):
                date = datetime.datetime.fromtimestamp(rfc822.mktime_tz(rfc822.parsedate_tz(line[6:]))).date()
            if line.startswith("Items:") or line.startswith("Subtotal of Items:"):
                itemsamount = -int(line.split()[-1].replace("$","").replace(".","").replace(",",""))
            if line.startswith("Order Total:") or line.startswith("Total for this Order:"):
                if items:
                    checkitems(items, amazontrans, amount, itemsamount, params)
                    items = []
                amount = -int(line.split()[-1].replace("$","").replace(".","").replace(",",""))
            if initems and line.startswith("****"):
                initems = False
            if initems:
                if not line:
                    if item:
                        item["amount"] = item["quantity"] * item["itemamount"]
                        item["id"] = "%s-%s-Amazon-%s" % (date, params["name"], hashlib.sha1(item["desc"]).hexdigest())
                        item["date"] = date
                        item["account"] = params["name"]
                        item["subaccount"] = "Amazon"
                        items.append(item)
                    item = {}
                else:
                    if line[0].isdigit():
                        item["quantity"] = int(line.split()[0])
                        item["attr_Quantity"] = line.split()[0]
                        item["desc"] = line.split(None,1)[1].strip('"')
                    elif line.startswith("$"):
                        item["itemamount"] =  -int(line.replace("$","").replace(".","").replace(",",""))
                    elif "$" in line:
                        item["attr_Amazon Category"] = line.split("; ")[0]
                        item["itemamount"] =  -int(line.split("; ")[-1].replace("$","").replace(".","").replace(",",""))
            if line.startswith("Delivery estimate"):
                initems = True
        if items:
            checkitems(items, amazontrans, amount, itemsamount, params)
        else:
            print "No items found! %s %s" % (date, amount)
        if date < params["lastcheck"]:
            break

    imap.close()
    imap.logout()

    return {}

if __name__ == "__main__":
    """Command-line driver"""

    if len(sys.argv) < 2:
        sys.exit(1)

    params = {}
    params["username"] = sys.argv[1]
    params["server"] = sys.argv[2]
    params["name"] = "Email"
    params["lastcheck"] = datetime.date.today()-datetime.timedelta(days=90)

    print "pyWebCash API Login"
    username = raw_input("Username: ")
    password = getpass.getpass()

    if not api.callapi("login",{"username": username, "password": password}):
        print "Login failed"
        sys.exit(1)

    params["seenids"] = [x["id"] for x in api.callapi("search", {"query": json.dumps({"account": params["name"]})})]
    print "Found %s old transactions" % (len(params["seenids"]))

    data = downloadaccount(None, params)

    api.callapi("logout")