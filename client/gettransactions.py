#!/usr/bin/python
# This is the main client-side scraping program.
# It will download a list of accounts, and run their scrapers.
import os
import sys
import api
import json
import getpass
import traceback
from selenium import webdriver

sys.path.append(os.path.dirname(__file__) + "/../")

import config

# Banks
banks = {}
for bank in config.banks:
    exec "import %s" % (bank)
    banks[bank] = eval(bank)

print "Login"
username = raw_input("Username: ")
password = getpass.getpass()

if not api.callapi("login",{"username": username, "password": password}):
    print "Login failed"
    sys.exit(1)

todo = api.callapi("accountstodo")

b = webdriver.Chrome()

for account in todo:
    if account["bankname"] not in banks:
        print "No scraper for %s!" % (account["bankname"])
        continue
    print "Scraping %s..." % (account["bankname"])
    try:
        if os.getenv("DATAFILE") and os.path.exists(account["bankname"]+".json"):
            data = open(account["bankname"]+".json").read()
        else:
            data = json.dumps(banks[account["bankname"]].downloadaccount(b, account),default=str)
            if os.getenv("DATAFILE"):
                open(account["bankname"]+".json","w").write(data)
        if not api.callapi("newtransactions", {"data": data}):
            print "Error uploading transactions"
    except Exception, e:
        print e
        traceback.print_exc()

b.close()

api.callapi("logout")
