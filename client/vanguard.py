#!/usr/bin/python
import os
import re
import sys
import time
import json
import common
import hashlib
import getpass
import datetime
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select

def downloadaccount(b, params):
    if "password" not in params:
        params["password"] = getpass.getpass("Vanguard Password for %s: " % (params["username"]))
    params.setdefault("name", "vanguard")
    params.setdefault("seenids",[])
    params.setdefault("lastcheck",datetime.date(2000,1,1))
    if type(params["lastcheck"]) in [ str, unicode ]:
        params["lastcheck"] = common.parsedate(params["lastcheck"])
    params["lastcheck"] -= datetime.timedelta(days=4)
    b.get("https://personal.vanguard.com/us/home?fromPage=portal")

    b.find_element_by_id("USER").send_keys(params["username"] + Keys.ENTER)
    
    while not b.find_elements_by_id("PASSWORD"):
        time.sleep(1)

    b.find_element_by_id("PASSWORD").send_keys(params["password"] + Keys.ENTER)
    
    balances = []

    accounts = b.find_elements_by_xpath("//tbody[@id='contentForm:whatIHaveTabBox:balanceForm:dcTabletbody0']/tr")

    # First and last two rows are not used
    for acct in accounts[2:-2]:
        balances.append({"account": params["name"], "subaccount": " ".join(acct.text.split()[:-1]), "balance": acct.text.split()[-1], "date": datetime.date.today()})

    b.find_element_by_link_text("LOG OFF").click()

    return { "balances": balances }
            
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
    json.dump(data, open("vanguard.json","w"), indent=2, default=str)
