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
        params["password"] = getpass.getpass("Wells Fargo Password for %s: " % (params["username"]))
    params.setdefault("name", "WellsFargo")
    params.setdefault("seenids",[])
    params.setdefault("lastcheck",datetime.date(2000,1,1))
    if type(params["lastcheck"]) in [ str, unicode ]:
        params["lastcheck"] = common.parsedate(params["lastcheck"])
    params["lastcheck"] -= datetime.timedelta(days=4)
    b.get("https://www.wellsfargo.com/")
    b.find_element_by_id("userid").send_keys(params["username"])
    b.find_element_by_id("password").send_keys(params["password"])
    b.find_element_by_id("btnSignon").click()
    while not b.find_elements_by_class_name("account"):
        time.sleep(1)
    transactions = []
    balances = []
    for i in range(len(b.find_elements_by_class_name("account"))):
        account = b.find_elements_by_class_name("account")[i].text
        b.find_elements_by_class_name("account")[i].click()
        balance = b.find_element_by_class_name("availableBalanceTotalAmount").text
        balances.append({"account": params["name"], "subaccount": account, "balance": balance, "date": datetime.date.today()})
        for row in b.find_elements_by_xpath("//table[@id='DDATransactionTable']/tbody/tr"):
            if row.text[0].isalpha():
                continue
            trans = { "account": params["name"], "subaccount": account}
            trans["date"] = datetime.datetime.strptime(row.find_element_by_class_name("date").text,"%m/%d/%y").date()
            trans["desc"] = row.find_element_by_class_name("text").text
            trans["amount"] = row.find_elements_by_class_name("amount")[0].text.strip()
            if not trans["amount"]:
                trans["amount"] = "-"+row.find_elements_by_class_name("amount")[1].text.strip()
            trans["id"] = "%s-%s-%s-%s" % (trans["date"], trans["account"], trans["subaccount"], hashlib.sha1(trans["desc"]).hexdigest())
            if trans["date"] < params["lastcheck"]:
                break
            if trans["id"] in params["seenids"]:
                continue
            transactions.append(trans)
        b.find_element_by_link_text("Account Summary").click()
    b.find_element_by_link_text("Sign Off").click()
    return {"transactions": transactions, "balances": balances}

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
    json.dump(data, open("wellsfargo.json","w"), indent=2, default=str)
