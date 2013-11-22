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
    common.loadcookies(b, params.get("cookies",[]))

    b.find_element_by_id("USER").send_keys(params["username"] + Keys.ENTER)

    while not b.find_elements_by_id("LoginForm:PASSWORD"):
        if b.find_elements_by_class_name("summaryTable"):
            question_text = b.find_element_by_class_name("summaryTable").text.lower()
            for question, answer in params.get("security_questions", {}).iteritems():
                if question.lower() in question_text:
                    b.find_element_by_name("ANSWER").send_keys(answer + Keys.ENTER)
                    del params["security_questions"][question]
                    break
        else:
            time.sleep(1)

    b.find_element_by_id("LoginForm:PASSWORD").send_keys(params["password"] + Keys.ENTER)
    
    balances = []

    accounts = b.find_elements_by_xpath("//tbody[@id='contentForm:whatIHaveTabBox:balanceForm:dcTabletbody0']/tr")

    # First and last two rows are not used
    for acct in accounts[2:-2]:
        balances.append({"account": params["name"], "subaccount": " ".join(acct.text.split()[:-1]), "balance": acct.text.split()[-1], "date": datetime.date.today()})

    if b.find_elements_by_link_text("LOG OFF"):
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
    params["cookies"] = json.load(open("cookies.json")) if os.path.exists("cookies.json") else []
    if os.path.exists("questions.json"):
        params["security_questions"] = json.load(open("questions.json"))
    b = webdriver.Chrome()
    data = downloadaccount(b, params)
    common.savecookies(b)
    b.quit()
    json.dump(data, open("vanguard.json","w"), indent=2, default=str)
