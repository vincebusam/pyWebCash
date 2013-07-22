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
from selenium.webdriver.support.ui import Select

def downloadaccount(b, params):
    if "password" not in params:
        params["password"] = getpass.getpass("FECU Password for %s: " % (params["username"]))
    params.setdefault("name", "FECU")
    params.setdefault("seenids",[])
    params.setdefault("lastcheck",datetime.date(2000,1,1))
    if type(params["lastcheck"]) in [ str, unicode ]:
        params["lastcheck"] = common.parsedate(params["lastcheck"])
    params["lastcheck"] -= datetime.timedelta(days=4)
    b.get("https://www.fefcu.org/cgi-bin/mcw000.cgi?MCWSTART")
    common.loadcookies(b, params.get("cookies",[]))
    b.find_element_by_name("HBUSERNAME").send_keys(params["username"])
    b.find_element_by_name("MCWSUBMIT").click()
    b.switch_to_frame(b.find_element_by_tag_name("iframe").get_attribute("id"))
    b.find_element_by_name("PASSWORD").send_keys(params["password"])
    b.find_element_by_tag_name("button").click()

    # Check for security questions...
    if b.find_elements_by_id("MCWSUBMIT"):
        b.find_element_by_id("MCWSUBMIT").click()
        b.find_element_by_id("MCWSUBMITCANCEL").click()
        b.find_element_by_link_text("here").click()

    # Get balances
    tables = ["mainShare", "mainLoan"]
    balances = []
    while not b.find_elements_by_id(tables[0]):
        time.sleep(1)
    for tableid in tables:
        for row in b.find_element_by_id(tableid).find_elements_by_class_name("standardrow"):
            data = [x.text for x in row.find_elements_by_tag_name("td")]
            if len(data) < 3:
                continue
            acct = data[1].rstrip("Skip-A-Pay").strip()
            balance = data[-1]
            # Look for interest rate to determine if it's a loan.
            if [x for x in data if "%" in x]:
                balance = "-" + balance
            balances.append({"account": params["name"], "subaccount": acct, "balance": balance, "date": datetime.date.today()})

    b.find_element_by_link_text("Exit").click()
    return {"balances": balances}

if __name__ == "__main__":

    if len(sys.argv) < 2:
        sys.exit(1)

    params = {}
    params["username"] = sys.argv[1]
    params["lastcheck"] = datetime.date.today()-datetime.timedelta(days=14)
    params["seenids"] = []
    params["cookies"] = json.load(open("cookies.json")) if os.path.exists("cookies.json") else []
    b = webdriver.Chrome()
    data = downloadaccount(b, params)
    common.savecookies(b)
    b.quit()
    json.dump(data, open("fecu.json","w"), indent=2, default=str)
