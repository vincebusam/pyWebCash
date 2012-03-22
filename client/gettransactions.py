#!/usr/bin/python
import sys
import api
import getpass

# Banks
banks = {}
import bankofamerica
banks["bankofamerica"] = bankofamerica

print "Login"
print "Username: ",
username = sys.stdin.readline().strip()
password = getpass.getpass()

if not api.callapi("login",{"username": username, "password": password}):
    print "Login failed"
    sys.exit(1)

todo = api.callapi("accountstodo")
print todo

for account in todo:
    if account["bankname"] not in banks:
        print "No scraper for %s!" % (account["bankname"])
        continue
    print "Scraping %s..." % (account["bankname"])
    #data = banks[account["bankname"].downloadaccount(account)

api.callapi("logout")
