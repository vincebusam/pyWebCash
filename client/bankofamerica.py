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
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select

def generateid(t):
    return "%s-%s-%s-%s" % (t["date"],t["account"],t["subaccount"],hashlib.sha1(t["desc"]).hexdigest())

datematch = re.compile("(\d{2})/(\d{2})/(\d{4})")

def showdetail(record, b):
    recordsshown = len(b.find_elements_by_class_name("record-detail"))
    if common.scrolluntilclick(b,record.find_element_by_class_name("date-action").find_element_by_tag_name("a")):
        while len(b.find_elements_by_class_name("record-detail")) <= recordsshown:
            time.sleep(0.1)

# Params - dict of name, username, password, state, date, seenids
def downloadaccount(b, params):
    # By default, we'll get all transactions since 2000!
    params.setdefault("lastcheck",datetime.date(2000,1,1))
    if type(params["lastcheck"]) in [ str, unicode ]:
        params["lastcheck"] = common.parsedate(params["lastcheck"])
    params["lastcheck"] -= datetime.timedelta(days=4)
    params.setdefault("seenids",[])
    params.setdefault("name","BofA")
    if not params.get("password"):
        params["password"] = getpass.getpass("BofA Password for %s: " % (params["username"]))
    b.get("https://www.bankofamerica.com/")
    if not b.find_elements_by_id("id"):
        if b.find_elements_by_name("olb-sign-in"):
            b.find_element_by_name("olb-sign-in").click()
        if b.find_elements_by_link_text("Continue to Online Banking"):
            b.find_element_by_link_text("Continue to Online Banking").click()
            b.find_element_by_id("enterID-input").send_keys(params["username"] + Keys.ENTER)
    else:
        b.find_element_by_id("id").send_keys(params["username"])
        Select(b.find_element_by_id("stateselect")).select_by_value(params["state"])
        b.find_element_by_id("top-button").click()
    while not b.find_elements_by_id("tlpvt-passcode-input"):
        if b.find_elements_by_id("VerifyCompForm"):
            question_text = b.find_element_by_id("VerifyCompForm").text.lower()
            for question, answer in params.get("security_questions", {}).iteritems():
                if question.lower() in question_text:
                    b.find_element_by_id("tlpvt-challenge-answer").send_keys(answer + Keys.ENTER)
                    del params["security_questions"][question]
                    break
        time.sleep(2)
    b.find_element_by_id("tlpvt-passcode-input").send_keys(params["password"])
    b.find_element_by_name("confirm-sitekey-submit").click()

    # Wait for user to continue to main screen
    while not b.find_elements_by_xpath("//div[contains(@class,'image-account')]/a"):
        if b.find_elements_by_link_text("Continue to Online Banking"):
            b.find_element_by_link_text("Continue to Online Banking").click()
        time.sleep(1)

    if b.find_elements_by_name("no_thanks"):
        b.find_element_by_name("no_thanks").click()

    accounts = []
    for a in b.find_elements_by_xpath("//div[contains(@class,'image-account')]/a"):
        if a.get_attribute("id") not in accounts:
            accounts.append(a.get_attribute("id"))
    newtransactions = []
    balances = []
    files = {}
    for acct in accounts:
        b.find_element_by_id(acct).click()
        for loop in range(len(b.find_elements_by_class_name("record"))):
            record = b.find_elements_by_class_name("record")[loop]
            transaction = {"account": params["name"], "subaccount": acct}
            date = record.find_element_by_class_name("date-action").find_elements_by_tag_name("span")[2].text
            m = datematch.match(date)
            if not m:
                continue
            transaction["date"] = datetime.datetime.strptime(date,"%m/%d/%Y").date()
            if transaction["date"] < params["lastcheck"]:
                break
            transaction["desc"] = record.find_element_by_class_name("description").find_elements_by_tag_name("span")[2].text.replace("\n","")
            transaction["amount"] = record.find_element_by_class_name("amount").text
            transaction["id"] = generateid(transaction)
            if transaction["id"] in params["seenids"]:
                continue
            showdetail(record, b)
            for line in b.find_elements_by_class_name("record-detail")[-1].text.replace(":\n",": ").split("\n"):
                if ":" in line:
                    transaction["attr_" + line.split(":")[0].strip()] = line.split(":")[1].strip()
            record_detail = b.find_elements_by_class_name("record-detail")[-1]
            if record_detail.find_elements_by_tag_name("img") and "deposit slip" not in record_detail.text.lower():
                image = record_detail.find_elements_by_tag_name("img")
                if image:
                    b.get(image[0].get_attribute("src"))
                    checkfn = transaction["id"] + ".png"
                    files[checkfn] = b.get_screenshot_as_base64()
                    b.back()
                    transaction["file"] = checkfn
                newtransactions.append(transaction)
                continue
            newtransactions.append(transaction)
            if record_detail.find_elements_by_tag_name("img") and "deposit slip" in record_detail.text.lower():
                for checkid in range(len(record_detail.find_elements_by_name("credit_check_thumbnail"))):
                    subtrans = {"account": params["name"],
                                "subaccount": acct,
                                "parents": [transaction["id"]],
                                "date": transaction["date"],
                                "desc": "BofA Check Deposit",
                                "id": "%s-%s" % (transaction["id"], checkid) }
                    subtrans["amount"] = record_detail.find_elements_by_name("credit_check_thumbnail")[checkid].text
                    if common.scrolluntilclick(b,record_detail.find_elements_by_name("credit_check_thumbnail")[checkid]):
                        b.get(record_detail.find_element_by_tag_name("img").get_attribute("src"))
                        checkfn = subtrans["id"] + ".png"
                        files[checkfn] = b.get_screenshot_as_base64()
                        b.back()
                        subtrans["file"] = checkfn
                    newtransactions.append(subtrans)
                    transaction.setdefault("children",[]).append(subtrans["id"])
                    record = b.find_elements_by_class_name("record")[loop]
                    showdetail(record, b)
                    record_detail = b.find_elements_by_class_name("record-detail")[-1]
        balance = b.find_element_by_class_name("TL_NPI_Amt").text
        balances.append({"account": params["name"], "subaccount": acct, "balance": balance, "date": datetime.date.today()})
        b.find_element_by_link_text("Accounts Overview").click()
    b.find_element_by_link_text("Sign Off").click()
    time.sleep(0.5)
    return {"transactions": newtransactions, "balances": balances, "files": files}

if __name__ == "__main__":

    if len(sys.argv) < 2:
        sys.exit(1)

    params = { "state": "CA" }
    params["username"] = sys.argv[1]
    params["lastcheck"] = datetime.date.today()-datetime.timedelta(days=int(os.getenv("DAYSBACK") or 14))
    params["seenids"] = []
    b = webdriver.Chrome()
    data = downloadaccount(b, params)
    b.quit()
    json.dump(data, open("bofa.json","w"), indent=2, default=str)
