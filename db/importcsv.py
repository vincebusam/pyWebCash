#!/usr/bin/python
import os
import db
import sys
import csv
import json
import hashlib
import getpass
import datetime

def parsedate(date):
    if "/" in date:
        return datetime.datetime.strptime(date,"%m/%d/%Y").date()
    if "-" in date:
        return datetime.datetime.strptime(date,"%Y-%m-%d").date()

header = []
headermap = { "description": "desc",
              "original description": "orig_desc",
              "transaction type": "type",
              "account name": "subaccount" }

dryrun = False
if sys.argv[1] == "-n":
    dryrun = True
    del sys.argv[1]

username = raw_input("Username: ")
password = getpass.getpass()
mydb = db.DB(username, password)
accounts = mydb.accounts()
accountnames = [x["name"] for x in accounts]
accountnames.append("Cash")
subaccountnames = {}
for acct in accounts:
    for sub in acct["subaccounts"]:
        subaccountnames[sub["name"]] = acct["name"]
accountmap = json.load(open("../accountmap.json"))

categories = mydb.getcategories()
subcats = {}
for cat in categories:
    for sc in categories[cat]:
        subcats[sc] = cat

unseensubaccounts = []
unseencategories = []

transactions = []
for row in csv.reader(open(sys.argv[1])):
    if not header:
        header = [headermap.get(x.lower(),x.lower()) for x in row]
        continue
    trans = dict([(header[x],row[x]) for x in range(len(row))])
    trans["subaccount"] = accountmap.get(trans["subaccount"],trans["subaccount"])
    if trans["subaccount"] in subaccountnames:
        trans["account"] = subaccountnames[trans["subaccount"]]
    elif trans["subaccount"] in accountnames:
        trans["account"] = trans["subaccount"]
        del trans["subaccount"]
    else:
        if trans["subaccount"] not in unseensubaccounts:
            unseensubaccounts.append(trans["subaccount"])
        trans["account"] = "Imported-Unmatched"
    if trans["category"] in subcats:
        trans["subcategory"] = trans["category"]
        trans["category"] = subcats[trans["subcategory"]]
    elif trans["category"] not in categories:
        if trans["category"] not in unseencategories:
            unseencategories.append(trans["category"])
    trans["amount"] = int(float(trans["amount"])*100)
    if trans["type"] == "debit":
        trans["amount"] = -trans["amount"]
    del trans["type"]
    trans["date"] = parsedate(trans["date"])
    [trans.pop(x) for x in trans.keys() if trans[x] in [ None, "" ]]
    trans["id"] = ("%s-%s-%s-%s" % (trans["date"],
                                    trans["account"],
                                    trans.get("subaccount"),
                                    hashlib.sha1(trans["desc"]).hexdigest())).replace(" ","")
    trans["state"] = "closed"
    trans["attr_Imported From"] = os.path.basename(sys.argv[1])
    transactions.append(trans)

# Squash transfers - match up with transfer to other account, set both of their amounts to 0
for i in range(len(transactions)):
    if transactions[i]["category"] == "Transfer" and \
       not "Cash" in transactions[i].get("subcategory","") and \
       not "parent" in transactions[i] and \
       not "child" in transactions[i]:
        for j in range(i+1,len(transactions)):
            if transactions[j]["category"] == "Transfer" and not "Cash" in transactions[j].get("subcategory","") and \
               transactions[i]["amount"] == -transactions[j]["amount"] and \
               not transactions[j].get("parent") and \
               not transactions[j].get("child") and \
               abs(transactions[i]["date"] - transactions[j]["date"]) <= datetime.timedelta(days=4):
                   transactions[i]["orig_amount"] = transactions[i]["amount"]
                   transactions[i]["amount"] = 0
                   transactions[j]["orig_amount"] = transactions[j]["amount"]
                   transactions[j]["amount"] = 0
                   transactions[i]["child"] = transactions[j]["id"]
                   transactions[j]["parent"] = transactions[i]["id"]

# Overkill to convert all dates to strings.
transactions = json.loads(json.dumps(transactions,default=str))
if not dryrun:
    mydb.newtransactions({"transactions": transactions}, autoprocess=False)

print "Imported %s transactions" % (len(transactions))
print unseensubaccounts
print unseencategories
