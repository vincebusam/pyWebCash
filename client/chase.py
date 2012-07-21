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
        params["password"] = getpass.getpass("Chase Password for %s: " % (params["username"]))
    params.setdefault("name", "Chase")
    params.setdefault("seenids",[])
    params.setdefault("lastcheck",datetime.date(2000,1,1))
    if type(params["lastcheck"]) in [ str, unicode ]:
        params["lastcheck"] = common.parsedate(params["lastcheck"])
    params["lastcheck"] -= datetime.timedelta(days=4)
    b.get("https://www.chase.com/")
    b.find_element_by_id("usr_name").send_keys(params["username"])
    b.find_element_by_id("usr_password").send_keys(params["password"])
    b.find_element_by_xpath("//div[@class='home_logon_button']/input").click()
    while not b.find_elements_by_partial_link_text("See activity"):
        time.sleep(1)
    b.find_element_by_partial_link_text("See activity").click()
    balance = b.find_element_by_class_name("first").text.split()[-1]
    if balance.startswith("-"):
        balance = balance.lstrip("-")
    else:
        balance = "-" + balance
    account = "Visa"
    balances = [{"account": params["name"], "subaccount": account, "balance": balance, "date": datetime.date.today()}]
    [common.scrolluntilclick(b,x) for x in b.find_elements_by_class_name("expander") if "closed" in x.get_attribute("class")]
    alltext = b.find_element_by_id("Posted").text + "\n"
    Select(b.find_element_by_id("StatementPeriodQuick")).select_by_value("LAST_STATEMENT")
    time.sleep(2)
    [x.click() for x in b.find_elements_by_class_name("expander") if "closed" in x.get_attribute("class")]
    alltext += b.find_element_by_id("Posted").text + "\n"
    b.find_element_by_partial_link_text("LOG OFF").click()
    
    transactions = []
    trans = {}
    for line in alltext.split("\n"):
        line = line.rstrip("Print").strip()
        if not line:
            continue
        if line.startswith("Trans Date"):
            continue
        if re.match("\d\d/\d\d/\d\d\d\d",line.split()[0]):
            trans = {"account": params["name"], "subaccount": account}
            trans["date"] = datetime.datetime.strptime(line.split()[0],"%m/%d/%Y").date()
            trans["attr_Post Date"] = line.split()[1]
            trans["attr_Type"] = line.split()[2]
            trans["desc"] = " ".join(line.split()[3:-1])
            trans["amount"] = line.split()[-1]
            if trans["amount"].startswith("-"):
                trans["amount"] = trans["amount"].lstrip("-")
            else:
                trans["amount"] = "-" + trans["amount"]
            trans["attr_Details"] = ""
            trans["id"] = "%s-%s-%s-%s" % (trans["date"], trans["account"], trans["subaccount"], hashlib.sha1(trans["desc"]).hexdigest())
            if trans["date"] < params["lastcheck"]:
                break
            if trans["id"] in params["seenids"]:
                trans = {}
                continue
            transactions.append(trans)
        elif trans:
            trans["attr_Details"] += " " + line.strip()
    
    return { "transactions": transactions, "balances": balances }
            
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
    json.dump(data, open("chase.json","w"), indent=2, default=str)
