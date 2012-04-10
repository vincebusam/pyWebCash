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
        params["password"] = getpass.getpass("PayPal Password for %s: " % (params["username"]))
    params.setdefault("name", "PayPal")
    params.setdefault("seenids",[])
    params.setdefault("lastcheck",datetime.date(2000,1,1))
    if type(params["lastcheck"]) in [ str, unicode ]:
        params["lastcheck"] = common.parsedate(params["lastcheck"])
    params["lastcheck"] -= datetime.timedelta(days=4)
    subaccount = "PayPal"
    b.get("https://www.paypal.com/")
    b.find_element_by_id("login_email").send_keys(params["username"])
    b.find_element_by_id("login_password").send_keys(params["password"])
    b.find_element_by_class_name("primary").click()

    # Get balance
    while not b.find_elements_by_xpath("//span[@class='balance']"):
        time.sleep(1)
    balance = b.find_element_by_xpath("//span[@class='balance']").text.lstrip().rstrip(" USD")
    balances = [{"account": params["name"], "subaccount": subaccount, "balance": balance, "date": datetime.date.today()}]

    # Go to transaction history
    transactions = []
    b.find_element_by_link_text("History").click()
    while not b.find_elements_by_id("dayoption"):
        time.sleep(1)
    Select(b.find_element_by_id("dayoption")).select_by_value("8")
    time.sleep(5)
    for row in b.find_element_by_id("transactionTable").find_elements_by_class_name("primary"):
        data = [x.text for x in row.find_elements_by_tag_name("td")]
        trans = { "account": params["name"],
                  "subaccount": subaccount,
                  "date": datetime.datetime.strptime(data[2], "%b %d, %Y").date(),
                  "desc": data[5],
                  "amount": data[-1].rstrip(" USD")
                }
        trans["id"] = "%s-%s-%s-%s" % (trans["date"], params["name"], subaccount, hashlib.sha1(trans["desc"]).hexdigest())
        if trans["date"] < params["lastcheck"]:
            break
        if trans["id"] in params["seenids"]:
            continue
        transactions.append(trans)
    b.find_element_by_link_text("Log Out").click()
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
    json.dump(data, open("paypal.json","w"), indent=2, default=str)
