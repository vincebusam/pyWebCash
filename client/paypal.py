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
        params["password"] = getpass.getpass("PayPal Password for %s: " % (params["username"]))
    params.setdefault("name", "PayPal")
    params.setdefault("seenids",[])
    params.setdefault("lastcheck",datetime.date(2000,1,1))
    if type(params["lastcheck"]) in [ str, unicode ]:
        params["lastcheck"] = common.parsedate(params["lastcheck"])
    params["lastcheck"] -= datetime.timedelta(days=4)
    subaccount = "PayPal"
    b.get("https://www.paypal.com/us/cgi-bin/webscr?cmd=_login-submit")
    #These break logging in for this site
    #common.loadcookies(b, params.get("cookies",[]))
    while not b.find_elements_by_id("login_email"):
        time.sleep(1)
    if b.find_element_by_id("login_email").text != params["username"]:
        b.find_element_by_id("login_email").send_keys(params["username"])
    b.find_element_by_id("login_password").send_keys(params["password"])
    if b.find_elements_by_class_name("primary"):
        b.find_element_by_class_name("primary").click()
    if b.find_elements_by_name("submit.x"):
        b.find_element_by_name("submit.x").click()

    balance = b.find_element_by_class_name("balanceNumeral").text.replace("Available","").strip()

    balances = [{"account": params["name"], "subaccount": subaccount, "balance": balance, "date": datetime.date.today()}]

    b.find_element_by_link_text("Activity").click()

    # Go to transaction history
    transactions = []

    time.sleep(2)

    for row in range(len(b.find_elements_by_class_name("activityRow"))):
        time.sleep(2)
        b.find_elements_by_class_name("activityRow")[row].click()
        if b.find_elements_by_id("transactionDetails"):
            data = b.find_element_by_id("transactionDetails").text
        elif b.find_elements_by_id("xptContentContainer"):
            data = b.find_element_by_id("xptContentContainer").text
        data = data.split("\n")
        for i in range(len(data)):
            line = data[i]
            try:
                date = datetime.datetime.strptime(" ".join(line.strip().split()[:3]), "%b %d, %Y").date()
            except ValueError:
                pass
            if line.strip().endswith("Name:"):
                desc = data[i+1].replace("(The recipient of this payment is Verified)").strip()
            if line.strip() == "Net amount:":
                amount = data[i+1].rstrip(" USD")
        trans = { "account": params["name"],
                  "subaccount": subaccount,
                  "date": date,
                  "desc": desc,
                  "amount": amount
                }
        trans["id"] = "%s-%s-%s-%s" % (trans["date"], params["name"], subaccount, hashlib.sha1(trans["desc"]).hexdigest())
        if trans["date"] < params["lastcheck"]:
            break
        if trans["id"] in params["seenids"]:
            continue
        transactions.append(trans)
        b.back()
        time.sleep(2)
    if b.find_elements_by_link_text("Log Out"):
        b.find_element_by_link_text("Log Out").click()
    if b.find_elements_by_class_name("logout"):
        b.find_element_by_class_name("logout").click()
    time.sleep(2)
    return {"transactions": transactions, "balances": balances}

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
    json.dump(data, open("paypal.json","w"), indent=2, default=str)
