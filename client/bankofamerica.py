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
        #for i in range(5):
        #    if b.find_elements_by_class_name("record-detail"):
        #        break
        #    time.sleep(1)
        while len(b.find_elements_by_class_name("record-detail")) <= recordsshown:
            time.sleep(0.1)

# Params - dict of name, username, password, state, date, seenids
def downloadaccount(b, params):
    # By default, we'll get all transactions since 2000!
    params.setdefault("lastcheck",datetime.date(2000,1,1))
    if type(params["lastcheck"]) in [ str, unicode ]:
        params["lastcheck"] = common.parsedate(params["lastcheck"])
    params.setdefault("enddate",datetime.date(2050,1,1))
    params["lastcheck"] -= datetime.timedelta(days=4)
    params.setdefault("seenids",[])
    params.setdefault("name","BofA")
    if not params.get("password"):
        params["password"] = getpass.getpass("BofA Password for %s: " % (params["username"]))
    b.get("https://www.bankofamerica.com/")
    common.loadcookies(b, params.get("cookies",[]))
    if b.find_elements_by_id("onlineId1"):
        b.find_element_by_id("onlineId1").send_keys(params["username"])
        b.find_element_by_id("passcode1").send_keys(params["password"] + Keys.ENTER)
    else:
        if not b.find_elements_by_id("id"):
            if b.find_elements_by_name("olb-sign-in"):
                b.find_element_by_name("olb-sign-in").click()
            if b.find_elements_by_link_text("Continue to Online Banking"):
                b.find_element_by_link_text("Continue to Online Banking").click()
                b.find_element_by_id("enterID-input").send_keys(params["username"] + Keys.ENTER)
        else:
            b.find_element_by_id("id").send_keys(params["username"])
            if b.find_elements_by_id("stateselect"):
                Select(b.find_element_by_id("stateselect")).select_by_value(params["state"])
            if b.find_elements_by_link_text("Sign In"):
                b.find_element_by_link_text("Sign In").click()
            if b.find_elements_by_id("hp-sign-in-btn"):
                b.find_element_by_id("hp-sign-in-btn").click()
            if b.find_elements_by_id("top-button"):
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

    if b.find_elements_by_id("VerifyCompForm"):
        if b.find_elements_by_id("yes-recognize"):
            b.find_element_by_id("yes-recognize").click()
        question_text = b.find_element_by_id("VerifyCompForm").text.lower()
        for question, answer in params.get("security_questions", {}).iteritems():
            if question.lower() in question_text:
                b.find_element_by_id("tlpvt-challenge-answer").send_keys(answer + Keys.ENTER)
                del params["security_questions"][question]
                break
    time.sleep(2)

    # Wait for user to continue to main screen
    while not b.find_elements_by_class_name("AccountName"):
        if b.find_elements_by_link_text("Continue to Online Banking"):
            b.find_element_by_link_text("Continue to Online Banking").click()
        time.sleep(1)

    if b.find_elements_by_name("no_thanks"):
        b.find_element_by_name("no_thanks").click()

    if b.find_elements_by_partial_link_text("close"):
        b.find_element_by_partial_link_text("close").click()

    accounts = []
    for a in b.find_elements_by_class_name("AccountName"):
        if a.text not in accounts:
            accounts.append(a.text)
    newtransactions = []
    balances = []
    files = {}
    for acct in accounts:
        b.find_element_by_link_text(acct).click()
        time.sleep(2)
        if acct[-4:].isdigit():
            acct = acct[:-7]
        while True:
            for loop in range(len(b.find_elements_by_class_name("record"))):
                if loop > len(b.find_elements_by_class_name("record")):
                    continue
                record = b.find_elements_by_class_name("record")[loop]
                transaction = {"account": params["name"], "subaccount": acct}
                date = record.find_element_by_class_name("date-action").find_elements_by_tag_name("span")[-1].text
                m = datematch.match(date)
                if not m:
                    continue
                transaction["date"] = datetime.datetime.strptime(date,"%m/%d/%Y").date()
                if transaction["date"] > params["enddate"]:
                    continue
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
                if record_detail.find_elements_by_tag_name("img") and ("deposit slip" not in record_detail.text.lower() or transaction["desc"] == "Counter Credit"):
                    image = [x.get_attribute("src") for x in record_detail.find_elements_by_tag_name("img") if "icon-bubble" not in x.get_attribute("src")]
                    if image:
                        b.get(image[0])
                        time.sleep(2.0)
                        checkfn = transaction["id"] + ".png"
                        files[checkfn] = b.get_screenshot_as_base64()
                        b.back()
                        time.sleep(1.0)
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
                            time.sleep(1.0)
                            checkfn = subtrans["id"] + ".png"
                            files[checkfn] = b.get_screenshot_as_base64()
                            b.back()
                            time.sleep(1.0)
                            subtrans["file"] = checkfn
                        newtransactions.append(subtrans)
                        transaction.setdefault("children",[]).append(subtrans["id"])
                        record = b.find_elements_by_class_name("record")[loop]
                        showdetail(record, b)
                        record_detail = b.find_elements_by_class_name("record-detail")[-1]
            else:
                if b.find_elements_by_link_text("Previous"):
                    common.scrolluntilclick(b,b.find_element_by_link_text("Previous"))
                    time.sleep(2)
                continue
            break
        balance = b.find_element_by_class_name("TL_NPI_Amt").text
        balances.append({"account": params["name"], "subaccount": acct, "balance": balance, "date": datetime.date.today()})
        if b.find_elements_by_link_text("Accounts Overview"):
            b.find_element_by_link_text("Accounts Overview").click()
        else:
            b.execute_script("fsdgoto('accountsoverview')")
    if b.find_elements_by_link_text("Sign Off"):
        b.find_element_by_link_text("Sign Off").click()
    time.sleep(0.5)
    return {"transactions": newtransactions, "balances": balances, "files": files}

if __name__ == "__main__":

    if len(sys.argv) < 2:
        sys.exit(1)

    params = { "state": "CA" }
    params["username"] = sys.argv[1]
    params["lastcheck"] = datetime.date.today()-datetime.timedelta(days=int(os.getenv("DAYSBACK") or 14))
    if os.getenv("ENDDATE"):
        params["enddate"] = common.parsedate(os.getenv("ENDDATE"))
    if os.getenv("STARTDATE"):
        params["lastcheck"] = common.parsedate(os.getenv("STARTDATE"))
    params["seenids"] = []
    params["cookies"] = json.load(open("cookies.json")) if os.path.exists("cookies.json") else []
    b = webdriver.Chrome()
    data = downloadaccount(b, params)
    common.savecookies(b)
    b.quit()
    json.dump(data, open("bofa.json","w"), indent=2, default=str)
