#!/usr/bin/python
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
import email.utils

apilock = None

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

    matchtransactions = api.callapi("search", {"query": json.dumps({"desc": "amzn.com/bill", "amount": "$lt:0"}), "startdate": str(datetime.date.today()-datetime.timedelta(days=14))})

    if not matchtransactions:
        print "No Amazon transactions open"
        return {}

    print "Searching for"
    for match in matchtransactions:
        print "%s %s" % (match["date"], match["amount"])

    imap = imaplib.IMAP4_SSL(params["server"])
    imap.login(params["username"],params["password"])
    imap.select(params["mailbox"])

    keepsearching = True
    for msg in sorted(map(int,imap.search(None, "FROM", "ship-confirm@amazon.com")[1][0].split()),reverse=True):
        out = StringIO.StringIO()
        messagetext = quopri.decode(StringIO.StringIO(imap.fetch(str(msg), "(RFC822)")[1][0][1]), out)
        out.seek(0)
        initems = False
        desc = ""
        amount = 0
        items = []
        for line in out.read().split("\n"):
            line = line.rstrip()
            if line.startswith("Date:"):
                date = str(datetime.datetime(*email.utils.parsedate_tz(line[7:])[:6]).date())
                if common.parsedate(date) < (common.parsedate(min([x["date"] for x in matchtransactions]))-datetime.timedelta(days=3)):
                    keepsearching = False
                    break
            if "Shipping and Handling" in line:
                amount = -int(line.split()[-1].replace("$","").replace(",","").replace(".",""))
                if items:
                    items[0]["amount"] += amount
            if "Sales Tax Collected" in line:
                amount = -int(line.split()[-1].replace("$","").replace(",","").replace(".",""))
                if items:
                    items[0]["amount"] += amount
            if "Shipment Total" in line:
                amount = -int(line.split()[-1].replace("$","").replace(",","").replace(".",""))
                if amount in [x["amount"] for x in matchtransactions]:
                    print "Matched up!"
                    if amount == sum([x["amount"] for x in items]):
                        index = [x["amount"] for x in matchtransactions].index(amount)
                        matched = matchtransactions.pop(index)
                        [x.update({"parents": [matched["id"]]}) for x in items]
                        if apilock:
                            apilock.acquire()
                        api.callapi("newtransactions", {"data": json.dumps({"transactions": items}, default=str)})
                        api.callapi("updatetransaction", {"id": matched["id"], "data": json.dumps({"amount":0, "children": [x["id"] for x in items]})})
                        if apilock:
                            apilock.release()
                    else:
                        print "Items don't add up!!"
                break
            if line.startswith("======"):
                initems = True
                continue
            if line.startswith("------"):
                initems = False
                continue
            if initems and line.strip() and not line.strip().startswith(line):
                if line.strip().startswith("$"):
                    amount = -int(line.strip().replace("$","").replace(",","").replace(".",""))
                    items.append({
                                    "date": date,
                                    "id": "%s-%s-Amazon-%s" % (date, params["name"], hashlib.sha1(desc).hexdigest()),
                                    "amount": amount,
                                    "desc": desc,
                                    "account": params["name"],
                                    "subaccount": "Amazon"
                                })
                    desc = ""
                else:
                    desc += (" " if desc else "") + line.strip()
        if not matchtransactions:
            print "Matched up all Amazon transactions"
            break
        if not keepsearching:
            print "Gone too far back in email"
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
