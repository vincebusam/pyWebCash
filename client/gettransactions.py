#!/usr/bin/python
import os
import sys
import api
import json
import getpass

sys.path.append("../")

import config

# Banks
banks = {}
for bank in config.banks:
    exec "import %s" % (bank)
    banks[bank] = eval(bank)

print "Login"
print "Username: ",
username = sys.stdin.readline().strip()
password = getpass.getpass()

if not api.callapi("login",{"username": username, "password": password}):
    print "Login failed"
    sys.exit(1)

todo = api.callapi("accountstodo")

for account in todo:
    if account["bankname"] not in banks:
        print "No scraper for %s!" % (account["bankname"])
        continue
    print "Scraping %s..." % (account["bankname"])
    if os.getenv("DATAFILE"):
        data = open(os.getenv("DATAFILE")).read()
    else:
        data = json.dumps(banks[account["bankname"]].downloadaccount(account),default=str)
    api.callapi("newtransactions", {"data": data})

api.callapi("logout")
