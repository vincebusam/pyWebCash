#!/usr/bin/python
# Scraper template
import re
import sys
import time
import json
import common
import hashlib
import getpass
import datetime
from selenium import webdriver
from selenium.webdriver.support.ui import Select

def downloadaccount(b, params):
    """Main function
        Args - b - webdriver browser
               params - dict of settings:
                 name - account name
                 username - login username
                 password - login password, if not given, use getpass to get it.
                 lastcheck - last seen transacation for this account, can stop checking a little after this date
                 seenids - list of last few seen transactions, to avoid dups
    """
    if "password" not in params:
        params["password"] = getpass.getpass("XXXX Password for %s: " % (params["username"]))
    params.setdefault("name", "XXXX")
    params.setdefault("seenids",[])
    params.setdefault("lastcheck",datetime.date(2000,1,1))
    if type(params["lastcheck"]) in [ str, unicode ]:
        params["lastcheck"] = common.parsedate(params["lastcheck"])
    params["lastcheck"] -= datetime.timedelta(days=4)
    b.get("https://www.example.com/")
    """Login, get transactions, balances, images"""

    """Array of dicts, each with account name, subaccount name, balance, current date"""
    balances = [{"account": params["name"], "subaccount": account, "balance": balance, "date": datetime.date.today()}]

    """Array of dicts, each with id, date, account, subaccount, desc, amount
       id should be YYYY-MM-DD-account-subaccount-uniqueid
       Account unique fields should start with attr_
    """
    transactions = []
    
    """dict of filenames (referenced in transactions as 'file' to base64 encoded png data"""
    files = {}
    
    return { "transactions": transactions, "balances": balances, "files": files }
            
if __name__ == "__main__":
    """Command-line driver"""

    if len(sys.argv) < 2:
        sys.exit(1)

    params = {}
    params["username"] = sys.argv[1]
    params["lastcheck"] = datetime.date.today()-datetime.timedelta(days=14)
    params["seenids"] = []
    b = webdriver.Chrome()
    data = downloadaccount(b, params)
    b.quit()
    json.dump(data, open("XXXX.json","w"), indent=2, default=str)
