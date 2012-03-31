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

def cardname(card):
    if "mastercard" in card.lower():
        return "MasterCard"
    if "MC" in card: #Only if upper-case
        return "MasterCard"
    if "american express" in card.lower():
        return "AmEx"
    if "amex" in card.lower():
        return "AmEx"

def parsetransaction(trans, lines):
    trans["date"] = datetime.datetime.strptime(lines[0].split()[0],"%m/%d/%Y").date()
    trans["dispamount"] = lines[0].split()[-1]
    trans["desc"] = " ".join(lines[0].split()[1:-1])
    # Need to negate amount!
    trans["amount"] = -int(trans["dispamount"].replace("$","").replace(".","").replace(",",""))
    for line in lines[1:]:
        if ":" in line:
            l = line.split(":",1)
            trans["attr_"+l[0]] = l[1].strip()
    trans["id"] = "%s-%s-%s-%s" % (trans["date"], trans["account"], trans["subaccount"], trans.get("attr_Reference Number",hashlib.sha1(trans["desc"]).hexdigest()))
    return trans

def downloadaccount(params):
    if "password" not in params:
        params["password"] = getpass.getpass("Citi Credit Cards Password for %s: " % (params["username"]))
    params.setdefault("name", "citicards")
    params.setdefault("seenids",[])
    params.setdefault("lastcheck",datetime.date(2000,1,1))
    if type(params["lastcheck"]) in [ str, unicode ]:
        params["lastcheck"] = common.parsedate(params["lastcheck"])
    params["lastcheck"] -= datetime.timedelta(days=4)
    b = webdriver.Chrome()
    b.get("https://creditcards.citi.com/")
    b.find_element_by_id("id").send_keys(params["username"])
    b.find_element_by_id("pw").send_keys(params["password"])
    b.find_element_by_class_name("login-submit").click()
    cards = [x.text for x in b.find_elements_by_class_name("card_info")]
    transactions = []
    balances = []
    for card in cards:
        for loop in range(5):
            if b.find_elements_by_link_text(card):
                break
            time.sleep(1)
        b.find_element_by_link_text(card).click()
        if not b.find_elements_by_class_name("curr_balance"):
            b.back()
            continue
        balance = b.find_element_by_class_name("curr_balance").text
        if balance == "$0.00":
            b.back()
            continue
        balances.append({"account": params["name"], "subaccount": cardname(card), "balance": -int(balance.replace("$","").replace(".","").replace(",","")), "date": datetime.date.today()})
        for page in range(3):
            if page:
                Select(b.find_element_by_id("date-select")).select_by_value(str(page))
                b.find_elements_by_xpath("//table[@id='transaction-details-search']//input")[-1].click()
                time.sleep(4)
            [x.click() for x in b.find_elements_by_class_name("activator")]
            skipped = 0
            for entry in b.find_elements_by_xpath("//table[@id='transaction-details-detail']//tbody"):
                if not entry.text:
                    continue
                trans = {"account": params["name"], "subaccount": cardname(card)}
                parsetransaction(trans, entry.text.split("\n"))
                if trans["date"] < params["lastcheck"]:
                    skipped += 1
                    continue
                if trans["id"] in params["seenids"]:
                    skipped += 1
                    continue
                transactions.append(trans)
            if skipped > 3:
                break
        b.back()
        time.sleep(1)
    b.find_element_by_xpath("//img[@alt='logout']").click()
    time.sleep(2)
    b.close()
    return {"transactions": transactions, "balances": balances}

if __name__ == "__main__":

    if len(sys.argv) < 2:
        sys.exit(1)

    params = {}
    params["username"] = sys.argv[1]
    params["lastcheck"] = datetime.date.today()-datetime.timedelta(days=14)
    params["seenids"] = []
    data = downloadaccount(params)
    json.dump(data, open("citicards.json","w"), indent=2, default=str)
