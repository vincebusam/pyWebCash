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
        params["password"] = getpass.getpass("Chase Password for %s: " % (params["username"]))
    params.setdefault("name", "Chase")
    params.setdefault("seenids",[])
    params.setdefault("lastcheck",datetime.date(2000,1,1))
    if type(params["lastcheck"]) in [ str, unicode ]:
        params["lastcheck"] = common.parsedate(params["lastcheck"])
    params["lastcheck"] -= datetime.timedelta(days=4)
    b.get("https://www.chase.com/")
    common.loadcookies(b, params.get("cookies",[]))

    b.find_element_by_id("usr_name_home").send_keys(params["username"])
    b.find_element_by_id("usr_password_home").send_keys(params["password"])
    b.find_elements_by_class_name("loginBtn")[-1].click()

    if b.find_elements_by_class_name("chaseui-modal"):
        b.find_element_by_class_name("chaseui-modal").click()

    if b.find_elements_by_id("show_go_to_my_accounts_img"):
        b.find_element_by_id("show_go_to_my_accounts_img").click()

    while not b.find_elements_by_partial_link_text("See activity"):
        time.sleep(1)
    common.scrolluntilclick(b, b.find_element_by_partial_link_text("See activity"))
    while not b.find_elements_by_class_name("first"):
        time.sleep(2)
    balance = b.find_elements_by_class_name("first")[-1].text.split()[-1]
    if balance.startswith("-"):
        balance = balance.lstrip("-")
    else:
        balance = "-" + balance

    # Remove this
    common.savecookies(b)

    account = "Visa"
    balances = [{"account": params["name"], "subaccount": account, "balance": balance, "date": datetime.date.today()}]
    [common.scrolluntilclick(b,x) for x in b.find_elements_by_class_name("expander") if "closed" in x.get_attribute("class")]
    alltext = b.find_element_by_id("Posted").text + "\n"
    cats = []
    if b.find_elements_by_name("categoryLabel0"):
        for catloop in range(1000):
            cats.append(Select(b.find_element_by_name("categoryLabel%i" % (catloop))).value)

    if b.find_elements_by_class_name("chaseui-modalclose"):
        b.find_element_by_class_name("chaseui-modalclose").click()
    b.execute_script("document.body.scrollTop=document.body.scrollTop+80;")
    for stmt in [ "LAST_STATEMENT", "TWO_STATEMENTS_PRIOR", "THREE_STATEMENTS_PRIOR" ]:
        if len(Select(b.find_element_by_id("StatementPeriodQuick")).options) > 1:
            for loop in range(10):
                try:
                    Select(b.find_element_by_id("StatementPeriodQuick")).select_by_value(stmt)
                    break
                except:
                    b.execute_script("document.body.scrollTop=document.body.scrollTop+20;")
            else:
                raise Exception("Couldn't select statememt period")
            time.sleep(2)
            [common.scrolluntilclick(b,x) for x in b.find_elements_by_class_name("expander") if "closed" in x.get_attribute("class")]
            alltext += b.find_element_by_id("Posted").text + "\n"
    common.scrolluntilclick(b,b.find_element_by_partial_link_text("Log Off"))
    #b.find_element_by_partial_link_text("Log Off").click()
    
    transactions = []
    trans = {}
    for line in alltext.split("\n"):
        if line.strip().endswith("Print"):
            line = line.replace("Print","").strip()
        if not line:
            continue
        if line.startswith("Trans Date"):
            continue
        if "Tag purchases with Jot" in alltext: # Business accounts
            if re.match("\d\d/\d\d/\d\d\d\d",line.split()[0]):
                trans = {"account": params["name"], "subaccount": account, "amount": 0}
                trans["date"] = datetime.datetime.strptime(line.split()[0],"%m/%d/%Y").date()
                trans["desc"] = line.split(" ",3)[3]
            elif line == "Print" or line.startswith("Memo50") or line.startswith("MiscellaneousAuto RelatedClothingComputer"):
                continue
            elif line.lstrip().startswith("$"):
                trans["amount"] = "-" + line.strip()
            elif line.startswith("Tag purchases with"):
                trans["id"] = "%s-%s-%s-%s" % (trans["date"], trans["account"], trans["subaccount"], hashlib.sha1(trans["desc"]).hexdigest())
                transactions.append(trans)
            elif "desc" in trans:
                trans["desc"] += " " + line
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
    params["lastcheck"] = datetime.date.today()-datetime.timedelta(days=180)
    params["seenids"] = []
    params["cookies"] = json.load(open("cookies.json")) if os.path.exists("cookies.json") else []
    b = webdriver.Chrome()
    data = downloadaccount(b, params)
    common.savecookies(b)
    b.quit()
    json.dump(data, open("chase.json","w"), indent=2, default=str)
