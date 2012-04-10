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
        params["password"] = getpass.getpass("GAP Password for %s: " % (params["username"]))
    params.setdefault("name", "GAP")
    params.setdefault("seenids",[])
    params.setdefault("lastcheck",datetime.date(2000,1,1))
    if type(params["lastcheck"]) in [ str, unicode ]:
        params["lastcheck"] = common.parsedate(params["lastcheck"])
    params["lastcheck"] -= datetime.timedelta(days=4)
    subaccount = "GapCard"
    b.get("https://www3.onlinecreditcenter6.com/consumergen2/login.do?subActionId=1000&clientId=gap&accountType=generic")
    b.find_element_by_name("userId").send_keys(params["username"])
    b.find_element_by_id("btn_login").click()
    b.find_element_by_name("password").send_keys(params["password"])
    b.find_element_by_id("btn_secure_Login").click()

    # Get balance
    while not b.find_elements_by_id("currentBalance"):
        time.sleep(1)
    balance = "-" + b.find_element_by_id("currentBalance").text
    balances = [{"account": params["name"], "subaccount": subaccount, "balance": balance, "date": datetime.date.today()}]

    # Go to transaction history
    b.find_element_by_partial_link_text("View Prior Activity").click()
    time.sleep(2)
    transactions = []
    for loop in range(2):
        if loop:
            Select(b.find_element_by_name("billingCombo")).select_by_index(loop)
            b.find_element_by_link_text("View").click()
            time.sleep(2)
        trans = {}
        if not b.find_elements_by_id("transactionDetailsTable"):
            continue
        for row in b.find_element_by_id("transactionDetailsTable").find_elements_by_tag_name("tr"):
            data = [x.text for x in row.find_elements_by_tag_name("td")]
            if not data[0]:
                trans["attr_Items"] = data[2]
                continue
            trans = { "account": params["name"],
                      "subaccount": subaccount,
                      "date": datetime.datetime.strptime(data[0], "%m/%d/%Y").date(),
                      "desc": data[2],
                      "amount": data[3],
                      "category": "Shopping",
                      "subcategory": "Clothing"
                    }
            if data[4] != "CR":
                trans["amount"] = "-" + trans["amount"]
            trans["id"] = "%s-%s-%s-%s" % (trans["date"], params["name"], subaccount, hashlib.sha1(trans["desc"]).hexdigest())
            if trans["date"] < params["lastcheck"]:
                break
            if trans["id"] in params["seenids"]:
                continue
            transactions.append(trans)
    b.find_element_by_link_text("Logout").click()
    time.sleep(2)
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
    json.dump(data, open("gap.json","w"), indent=2, default=str)
