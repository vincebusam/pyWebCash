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
        params["password"] = getpass.getpass("UESP Password for %s: " % (params["username"]))
    params.setdefault("name", "UESP")
    params.setdefault("seenids",[])
    params.setdefault("lastcheck",datetime.date(2000,1,1))
    if type(params["lastcheck"]) in [ str, unicode ]:
        params["lastcheck"] = common.parsedate(params["lastcheck"])
    params["lastcheck"] -= datetime.timedelta(days=4)
    b.get("https://login.uesp.org/")

    b.find_element_by_id("ctl00_ctl00_Content_Content_userNameTextBox").send_keys(params["username"])
    b.find_element_by_id("ctl00_ctl00_Content_Content_loginButton").click()
    b.find_element_by_id("ctl00_ctl00_Content_Content_passwordTextBox").send_keys(params["password"])
    b.find_element_by_id("ctl00_ctl00_Content_Content_loginButton").click()

    balances = []
    for child in b.find_elements_by_class_name("groupOutlines"):
        
        balances.append({"account": params["name"],
                         "subaccount": child.text.split("\n")[0].split(":",1)[1].strip(),
                         "balance": child.text.split("\n")[2].split(":",1)[1].strip(),
                         "date": datetime.date.today()})

    b.find_element_by_id("ctl00_ctl00_Content_btnLogout").click()

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
    json.dump(data, open("uesp.json","w"), indent=2, default=str)
