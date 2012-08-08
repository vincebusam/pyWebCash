#!/usr/bin/python
# This is the main client-side scraping program.
# It will download a list of accounts, and run their scrapers.
import os
import sys
import api
import json
import time
import getpass
import threading
import traceback
from selenium import webdriver

sys.path.append((os.path.dirname(__file__) or ".") + "/../")

import config

class scrapethread(threading.Thread):

    def __init__(self, b, account):
        self.b = b
        self.account = account
        threading.Thread.__init__(self)

    def run(self):
        try:
            data = json.dumps(banks[account["bankname"]].downloadaccount(self.b, self.account), default=str)
        except Exception, e:
            print e
            traceback.print_exc()
            return
        if os.getenv("DATAFILE"):
            open(self.account["bankname"]+".json","w").write(data)
        apilock.acquire()
        if not api.callapi("newtransactions", {"data": data}):
            print "Error uploading transactions for %s" % (self.account["bankname"])
        apilock.release()

apilock = threading.Lock()

# Banks
banks = {}
for bank in config.banks:
    exec "import %s" % (bank)
    banks[bank] = eval(bank)
    banks[bank].apilock = apilock

print "Login"
username = raw_input("Username: ")
password = getpass.getpass()

if not api.callapi("login",{"username": username, "password": password}):
    print "Login failed"
    sys.exit(1)

todo = api.callapi("accountstodo")
questions = api.callapi("getquestions")

for account in todo:
    account.setdefault("security_questions", questions)
    if account.get("username") and "password" not in account:
        account["password"] = getpass.getpass("Password for %s (%s): " % (account["name"], account["username"]))

config.threads = min(config.threads, len(todo))

b = [webdriver.Chrome() for x in range(config.threads)]
threads = [None for x in range(config.threads)]

for account in todo:
    if account["bankname"] not in banks:
        print "No scraper for %s!" % (account["bankname"])
        continue
    print "Scraping %s..." % (account["bankname"])
    if os.getenv("DATAFILE") and os.path.exists(account["bankname"]+".json"):
        data = open(account["bankname"]+".json").read()
        apilock.acquire()
        if not api.callapi("newtransactions", {"data": data}):
            print "Error uploading transactions"
        apilock.release()
    else:
        for t in range(config.threads):
            if threads[t] == None:
                threads[t] = scrapethread(b[t], account)
                threads[t].start()
                break
    while len([x for x in threads if x]) == config.threads:
        for t in range(config.threads):
            if threads[t] and not threads[t].is_alive():
                threads[t].join()
                threads[t] = None
        if len([x for x in threads if x]) == config.threads:
            time.sleep(1)

print "Waiting for scrapers..."
for t in range(config.threads):
    if threads[t]:
        threads[t].join()
    b[t].quit()

api.callapi("logout")
