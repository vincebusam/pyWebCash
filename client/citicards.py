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
    trans["date"] = datetime.datetime.strptime(lines[0],"%m-%d-%Y").date()
    trans["orig_amount_str"] = lines[-1]
    trans["desc"] = lines[1]
    trans["attr_Merchant Category"] = lines[2]
    # Need to negate amount!
    if trans["orig_amount_str"].startswith("("):
        trans["orig_amount_str"] = "-" + trans["orig_amount_str"].strip("()")
    trans["amount"] = -int(trans["orig_amount_str"].replace("$","").replace(".","").replace(",",""))
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
            time.sleep(2)
        else:
            raise Exception("Couldn't find card %s" % (card))
        while True:
            try:
                b.find_element_by_link_text(card).click()
                break
            except:
                b.execute_script("document.body.scrollTop=document.body.scrollTop+40;")
        time.sleep(4)
        while b.find_elements_by_id("cmlink_NoClosedAccountOverlay"):
            b.find_element_by_link_text("Cancel and Continue to Account Details").click()
            time.sleep(1)
        if b.find_elements_by_class_name("cT-labelItem")and "Current Balance" in b.find_elements_by_class_name("cT-labelItem")[0].text:
            balance = b.find_elements_by_class_name("cT-valueItem")[0].text.replace(" ","")
            if balance != "$0.00":
                balances.append({"account": params["name"], "subaccount": cardname(card), "balance": -int(balance.replace("$","").replace(".","").replace(",","")), "date": datetime.date.today()})
        for page in range(6):
            if page:
                common.scrolluntilclick(b,b.find_elements_by_class_name("ui-selectmenu")[-1])
                b.execute_script("document.body.scrollTop=document.body.scrollTop+40;")
                if not b.find_elements_by_id("filterDropDown-menu-option-%s" % (page)):
                    break
                common.scrolluntilclick(b.find_element_by_id("filterDropDown-menu-option-%s" % (page)))
                time.sleep(4)

            skipped = 0
            for entry in b.find_elements_by_class_name("purchase"):
                while True:
                    try:
                        entry.find_element_by_class_name("cM-maximizeButton").click()
                        break
                    except:
                        b.execute_script("document.body.scrollTop=document.body.scrollTop+40;")
                else:
                    print "ERROR"
                trans = {"account": params["name"], "subaccount": cardname(card)}
                parsetransaction(trans, entry.text.split("\n"))
                details = b.find_element_by_id(entry.get_attribute("id").replace("-","Ext-"))
                for i in range(len(details.find_elements_by_class_name("cT-labelItem"))):
                    trans["attr_"+details.find_elements_by_class_name("cT-labelItem")[i].text] = details.find_elements_by_class_name("cT-valueItem")[i].text
                trans["id"] = "%s-%s-%s-%s" % (trans["date"], trans["account"], trans["subaccount"], trans.get("attr_Reference Number",hashlib.sha1(trans["desc"]).hexdigest()))
                if trans["date"] < params["lastcheck"]:
                    skipped += 1
                    continue
                if trans["id"] in params["seenids"]:
                    skipped += 1
                    continue
                if trans["id"] in [x["id"] for x in transactions]:
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
    b.execute_script("document.body.scrollTop=0;")
    if b.find_elements_by_class_name("signOffBtn"):
        common.scrolluntilclick(b,b.find_element_by_class_name("signOffBtn"))
    elif b.find_elements_by_link_text("Sign Off"):
        common.scrolluntilclick(b,b.find_element_by_link_text("Sign Off"))
    time.sleep(2)
    if not transactions or not balances:
        print "!!! citicards - No balances or transactions found !!!"
    return {"transactions": transactions, "balances": balances}

if __name__ == "__main__":

    if len(sys.argv) < 2:
        sys.exit(1)

    params = {}
    params["username"] = sys.argv[1]
    params["lastcheck"] = datetime.date.today()-datetime.timedelta(days=120)
    params["seenids"] = []
    params["cookies"] = json.load(open("cookies.json")) if os.path.exists("cookies.json") else []
    b = webdriver.Chrome()
    data = downloadaccount(b, params)
    common.savecookies(b)
    b.quit()
    json.dump(data, open("citicards.json","w"), indent=2, default=str)
