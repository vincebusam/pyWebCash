#!/usr/bin/python
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
        params["password"] = getpass.getpass("Provident Password for %s: " % (params["username"]))
    params.setdefault("name", "Provident")
    params.setdefault("seenids",[])
    params.setdefault("lastcheck",datetime.date(2000,1,1))
    if type(params["lastcheck"]) in [ str, unicode ]:
        params["lastcheck"] = common.parsedate(params["lastcheck"])
    params["lastcheck"] -= datetime.timedelta(days=4)
    b.get("https://www.provident.com/")
    b.find_element_by_link_text("Log In").click()
    b.find_element_by_id("ctl00_ctl00_cphCenter_cphContent_txtUserName").send_keys(params["username"])
    b.find_element_by_id("ctl00_ctl00_cphCenter_cphContent_txtPassword").send_keys(params["password"])
    b.find_element_by_id("ctl00_ctl00_cphCenter_cphContent_btnLogin").click()
    b.find_element_by_id("ctl00_ctl00_cphCenter_cphContent_LoanServicedByPFDataGrid_ctl02_ClickButton").click()
    while not b.find_elements_by_id("ctl00_ctl00_cphCenter_cphContent__propertyStreetAddressLabel"):
        time.sleep(1)
    subaccount = b.find_element_by_id("ctl00_ctl00_cphCenter_cphContent__propertyStreetAddressLabel").text
    balance = "-" + b.find_element_by_id("ctl00_ctl00_cphCenter_cphContent__currLoanBalLabel").text
    balances = [{"account": params["name"], "subaccount": subaccount, "balance": balance, "date": datetime.date.today()}]
    b.find_element_by_link_text("Logout").click()
    return {"balances": balances}

if __name__ == "__main__":

    if len(sys.argv) < 2:
        sys.exit(1)

    params = {}
    params["username"] = sys.argv[1]
    params["lastcheck"] = datetime.date.today()-datetime.timedelta(days=14)
    params["seenids"] = []
    b = webdriver.Chrome()
    data = downloadaccount(b, params)
    b.quit()
    json.dump(data, open("provident.json","w"), indent=2, default=str)
