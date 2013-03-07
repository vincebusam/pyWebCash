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
        params["password"] = getpass.getpass("Fidelity Password for %s: " % (params["username"]))
    params.setdefault("name", "Fidelity")
    params.setdefault("seenids",[])
    params.setdefault("lastcheck",datetime.date(2000,1,1))
    if type(params["lastcheck"]) in [ str, unicode ]:
        params["lastcheck"] = common.parsedate(params["lastcheck"])
    params["lastcheck"] -= datetime.timedelta(days=4)
    b.get("https://www.fidelity.com/")

    b.find_element_by_link_text("Log In").click()
    b.find_element_by_id("userId").send_keys(params["username"])
    b.find_element_by_id("password").send_keys(params["password"] + Keys.ENTER)

    balances = []

    for account in [x.text for x in b.find_elements_by_xpath("//table[@class='datatable-component']//tr") if '$' in x.text and "total" not in x.text.lower()]:
        balances.append({"account": params["name"], "subaccount": account.split("\n")[0], "balance": account.split("\n")[-1], "date": datetime.date.today()})

    b.find_element_by_link_text("Log Out").click()

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
    json.dump(data, open("fidelity.json","w"), indent=2, default=str)
