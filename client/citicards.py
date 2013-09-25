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
    trans["orig_amount_str"] = lines[0].split()[-1]
    trans["desc"] = " ".join(lines[0].split()[1:-1])
    # Need to negate amount!
    trans["amount"] = -int(trans["orig_amount_str"].replace("$","").replace(".","").replace(",",""))
    for line in lines[1:]:
        if ":" in line:
            l = line.split(":",1)
            trans["attr_"+l[0]] = l[1].strip()
    trans["id"] = "%s-%s-%s-%s" % (trans["date"], trans["account"], trans["subaccount"], trans.get("attr_Reference Number",hashlib.sha1(trans["desc"]).hexdigest()))
    return trans

def downloadaccount(b, params):
    if "password" not in params:
        params["password"] = getpass.getpass("Citi Credit Cards Password for %s: " % (params["username"]))
    params.setdefault("name", "citicards")
    params.setdefault("seenids",[])
    params.setdefault("lastcheck",datetime.date(2000,1,1))
    if type(params["lastcheck"]) in [ str, unicode ]:
        params["lastcheck"] = common.parsedate(params["lastcheck"])
    params["lastcheck"] -= datetime.timedelta(days=4)
    b.get("https://creditcards.citi.com/")
    common.loadcookies(b, params.get("cookies",[]))
    if b.find_elements_by_id("id"):
        b.find_element_by_id("id").send_keys(params["username"])
    elif b.find_elements_by_id("cA-cardsUseridMasked"):
        b.find_element_by_id("cA-cardsUseridMasked").send_keys(params["username"])
    if b.find_elements_by_id("pw"):
        b.find_element_by_id("pw").send_keys(params["password"])
    elif b.find_elements_by_name("PASSWORD"):
        b.find_element_by_name("PASSWORD").send_keys(params["password"])
    if b.find_elements_by_class_name("login-submit"):
        b.find_element_by_class_name("login-submit").click()
    elif b.find_element_by_class_name("cA-cardsLoginSubmit"):
        b.find_element_by_class_name("cA-cardsLoginSubmit").click()
    cards = [x.text for x in b.find_elements_by_class_name("cT-accountName") if x.find_elements_by_tag_name("a")]
    transactions = []
    balances = []
    for card in cards:
        for loop in range(5):
            if b.find_elements_by_link_text(card):
                break
            time.sleep(1)
        b.find_element_by_link_text(card).click()
        while b.find_elements_by_id("cmlink_NoClosedAccountOverlay"):
            print "citicards: Go manually say no"
            time.sleep(1)
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
                try:
                    Select(b.find_element_by_id("date-select")).select_by_value(str(page))
                except:
                    break
                b.find_elements_by_xpath("//table[@id='transaction-details-search']//input")[-1].click()
                time.sleep(4)
            activators = b.find_element_by_xpath("//table[@id='transaction-details-detail']").find_elements_by_class_name("activator")
            common.scrolluntilclick(b,b.find_element_by_id("transaction-title"))
            skipped = 0
            for entry in b.find_elements_by_xpath("//table[@id='transaction-details-detail']//tbody"):
                if not entry.text:
                    continue
                if activators:
                    b.execute_script("document.body.scrollTop=document.body.scrollTop+40;")
                    act = activators.pop(0)
                    while "Transaction" not in entry.text:
                        b.execute_script("document.body.scrollTop=document.body.scrollTop+40;")
                        act.click()
                trans = {"account": params["name"], "subaccount": cardname(card)}
                if not entry or not entry.text[0].isdigit():
                    continue
                parsetransaction(trans, entry.text.split("\n"))
                if trans["date"] < params["lastcheck"]:
                    skipped += 1
                    continue
                if trans["id"] in params["seenids"]:
                    skipped += 1
                    continue
                if trans["id"] in [x["id"] for x in transactions]:
                    print "Dup Reference Number!!"
                    trans["id"] += "-" + str(abs(trans["amount"]))
                transactions.append(trans)
                if len(transactions) == 5:
                    if len([x for x in transactions if "attr_Merchant Category" in x]) == 0:
                        print "Warning, not enough Merchant Categories found!!!"
                        raise Exception("No merchant categories found!")
            if skipped > 3:
                break
        b.back()
        time.sleep(1)
    if b.find_elements_by_class_name("signOffBtn"):
        b.find_element_by_class_name("signOffBtn").click()
    elif b.find_elements_by_link_text("Sign Off"):
        b.find_element_by_link_text("Sign Off").click()
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
    json.dump(data, open("citicards.json","w"), indent=2, default=str)
