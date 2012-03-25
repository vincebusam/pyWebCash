#!/usr/bin/python
import re
import sys
import time
import json
import hashlib
import getpass
import datetime
from selenium import webdriver
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.keys import Keys

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
    date = lines[0].split()[0].split("/")
    trans["date"] = "%s-%s-%s" % (date[2],date[0],date[1])
    trans["dispamount"] = lines[0].split()[-1]
    # Need to negate amount!
    trans["amount"] = -int(trans["dispamount"].replace("$","").replace(".","").replace(",",""))
    trans["desc"] = " ".join(lines[0].split()[1:-1])
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
        [x.click() for x in b.find_elements_by_class_name("activator")]
        for entry in b.find_elements_by_xpath("//table[@id='transaction-details-detail']//tbody"):
            if not entry.text:
                continue
            trans = {"account": params["name"], "subaccount": cardname(card)}
            parsetransaction(trans, entry.text.split("\n"))
            transactions.append(trans)
        Select(b.find_element_by_id("date-select")).select_by_value("1")
        b.find_elements_by_xpath("//table[@id='transaction-details-search']//input")[-1].click()
        time.sleep(4)
        [x.click() for x in b.find_elements_by_class_name("activator")]
        for entry in b.find_elements_by_xpath("//table[@id='transaction-details-detail']//tbody"):
            if not entry.text:
                continue
            trans = {"account": params["name"], "subaccount": cardname(card)}
            parsetransaction(trans, entry.text.split("\n"))
            transactions.append(trans)
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
