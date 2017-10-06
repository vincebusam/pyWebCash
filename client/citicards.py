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
    raise Exception("Unknown card %s" % (card))

def parsetransaction(trans, lines):
    trans["date"] = datetime.datetime.strptime(lines[0],"%b. %d, %Y").date()
    for l in reversed(lines):
        trans["orig_amount_str"] = l
        try:
            # Need to negate amount!
            if trans["orig_amount_str"].startswith("("):
                trans["orig_amount_str"] = "-" + trans["orig_amount_str"].strip("()")
            trans["amount"] = -int(trans["orig_amount_str"].replace("$","").replace(".","").replace(",",""))
        except:
            break
    trans["desc"] = lines[1]
    try:
        trans["attr_Merchant Category"] = filter(lambda x: x.startswith("Category:"),lines)[0].replace("Category: ","")
    except:
        pass
    trans.update(dict([("attr_"+x.split(":")[0],x.split(":",1)[1].strip()) for x in lines if ":" in x]))
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
    if b.find_element_by_class_name("cA-cardsLoginSubmit"):
        b.find_element_by_class_name("cA-cardsLoginSubmit").click()
    for loop in range(10):
        time.sleep(1)
        if b.find_elements_by_link_text("No Thanks"):
            common.scrolluntilclick(b,b.find_element_by_link_text("No Thanks"))
            time.sleep(1)
        cards = [x.text for x in b.find_elements_by_class_name("cA-spf-cardArtHeader") if x.find_elements_by_tag_name("a")]
        if cards:
            break
    transactions = []
    balances = []
    for card in cards:
        for loop in range(5):
            if b.find_elements_by_link_text(card):
                break
            time.sleep(10)
        else:
            raise Exception("Couldn't find card %s" % (card))
        while True:
            try:
                b.find_element_by_link_text(card).click()
                break
            except:
                b.execute_script("window.scrollBy(0,40);")
        time.sleep(4)
        while b.find_elements_by_id("cmlink_NoClosedAccountOverlay"):
            b.find_element_by_link_text("Cancel and Continue to Account Details").click()
            time.sleep(1)
        if b.find_elements_by_class_name("cA-ada-firstBalanceElementValue"):
            balance = b.find_element_by_class_name("cA-ada-firstBalanceElementValue").text.replace(" ","")
            if balance != "$0.00":
                balances.append({"account": params["name"], "subaccount": cardname(card), "balance": -int(balance.replace("$","").replace(".","").replace(",","")), "date": datetime.date.today()})
        for page in range(6):
            if page:
                Select(b.find_element_by_id("statementFilterDropDown")).select_by_index(page)
                time.sleep(4)

            skipped = 0
            for entry in b.find_elements_by_class_name("purchase"):
                for loop in range(40):
                    try:
                        entry.find_element_by_class_name("cA-ada-expandLinkContainer").click()
                        break
                    except:
                        b.execute_script("window.scrollBy(0,40);")
                    if entry.find_elements_by_class_name("cM-minimizeButton"):
                        break
                else:
                    print "ERROR"
                trans = {"account": params["name"], "subaccount": cardname(card)}
                parsetransaction(trans, entry.text.split("\n"))
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
        b.execute_script("window.scrollTo(0,0);")
        common.scrolluntilclick(b,b.find_element_by_link_text("Accounts"))
        time.sleep(4)
    b.execute_script("window.scrollTo(0,0);")
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
