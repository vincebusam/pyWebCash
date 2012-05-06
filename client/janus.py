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
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select


def downloadaccount(b, params):
    if "password" not in params:
        params["password"] = getpass.getpass("Janus Password for %s: " % (params["username"]))
    params.setdefault("name", "Janus")
    params.setdefault("seenids",[])
    params.setdefault("lastcheck",datetime.date(2000,1,1))
    if type(params["lastcheck"]) in [ str, unicode ]:
        params["lastcheck"] = common.parsedate(params["lastcheck"])
    params["lastcheck"] -= datetime.timedelta(days=4)
    b.get("https://www.janus.com/")
    if b.find_elements_by_id("selimg4"):
        b.find_element_by_id("selimg4").click()
        b.find_element_by_link_text("Log in to My Account").click()
    
    b.find_element_by_id("ssn").send_keys(params["username"] + Keys.TAB + params["password"] + Keys.ENTER)
    
    balances = []
    inaccounts = False
    name = ""
    for line in b.find_element_by_id("nonretirementAccountdata").text.split("\n"):
        if inaccounts:
            if not name:
                name = line
            else:
                balances.append({"account": params["name"], "subaccount": name, "balance": line, "date": datetime.date.today()})
                name = ""
        if line == "Current Balance":
            inaccounts = True
        if "Total" in line:
            break

    b.find_element_by_name("logout").click()

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
    json.dump(data, open("janus.json","w"), indent=2, default=str)
