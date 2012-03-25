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

def generateid(t):
    return "%s-%s-%s-%s" % (t["date"],t["account"],t["subaccount"],hashlib.sha1(t["desc"]).hexdigest())

datematch = re.compile("(\d{2})/(\d{2})/(\d{4})")

splitdate = lambda x: map(int,x.split("-"))
parsedate = lambda x: datetime.date(splitdate(x)[0],splitdate(x)[1],splitdate(x)[2])

# Params - dict of name, username, password, state, date, seenids
def downloadaccount(params):
    # By default, we'll get all transactions since 2000!
    params.setdefault("lastcheck",datetime.date(2000,1,1))
    if type(params["lastcheck"]) in [ str, unicode ]:
        params["lastcheck"] = parsedate(params["lastcheck"])
    params["lastcheck"] -= datetime.timedelta(days=4)
    params.setdefault("seenids",[])
    params.setdefault("name","BofA")
    if not params.get("password"):
        params["password"] = getpass.getpass("BofA Password for %s: " % (params["name"]))
    b = webdriver.Chrome()
    b.get("https://www.bankofamerica.com/")
    b.find_element_by_id("id").send_keys(params["username"])
    Select(b.find_element_by_id("stateselect")).select_by_value(params["state"])
    b.find_element_by_id("top-button").click()
    while not b.find_elements_by_id("tlpvt-passcode-input"):
        time.sleep(5)
    b.find_element_by_id("tlpvt-passcode-input").send_keys(params["password"])
    b.find_element_by_name("confirm-sitekey-submit").click()
    accounts = []
    for a in b.find_elements_by_xpath("//div[contains(@class,'image-account')]/a"):
        if a.get_attribute("id") not in accounts:
            accounts.append(a.get_attribute("id"))
    newtransactions = []
    balances = []
    files = {}
    for acct in accounts:
        print "Download transactions from %s" % (acct)
        b.find_element_by_id(acct).click()
        for loop in range(1000):
            transaction = {"account": params["name"], "subaccount": acct}
            if not b.find_elements_by_id("row%s" % (loop)):
                break
            date = b.find_element_by_xpath("//tr[@id='row%s']/td[3]" % (loop)).text
            m = datematch.match(date)
            if not m:
                continue
            transaction["date"] = datetime.date(int(m.group(3)),int(m.group(1)),int(m.group(2)))
            if transaction["date"] < params["lastcheck"]:
                break
            transaction["desc"] = b.find_element_by_xpath("//tr[@id='row%s']/td[4]" % (loop)).text.replace("\n","")
            transaction["amount"] = b.find_element_by_xpath("//tr[@id='row%s']/td[7]" % (loop)).text
            transaction["id"] = generateid(transaction)
            if transaction["id"] in params["seenids"]:
                print "Already have %s" % (transaction["id"])
                continue
            if common.scrolluntilclick(b,b.find_element_by_id("rtImg%i"%(loop))):
                for line in b.find_element_by_id("exptd%s"%(loop)).text.split("\n"):
                    if ":" in line:
                        transaction["attr_" + line.split(":")[0].strip()] = line.split(":")[1].strip()
            if b.find_elements_by_id("ViewImgFront"):
                b.find_element_by_id("ViewImgFront").click()
                image = [x for x in b.find_elements_by_xpath("//tr[@id='exp0']//img") if "/cgi-bin" in x.get_attribute("src")]
                if image:
                    b.get(image[0].get_attribute("src"))
                    checkfn = transaction["id"] + ".png"
                    files[checkfn] = b.get_screenshot_as_base64()
                    b.back()
                    transaction["file"] = checkfn
            newtransactions.append(transaction)
            if b.find_elements_by_id("ViewImages"):
                common.scrolluntilclick(b,b.find_element_by_id("ViewImages"))
                for checkid in range(1,20):
                    if not b.find_elements_by_id("icon%s"%(checkid)):
                        continue
                    subtrans = {"account": params["name"],
                                "subaccount": acct,
                                "parent": transaction["id"],
                                "date": transaction["date"],
                                "desc": "BofA Check Deposit",
                                "id": "%s-%s" % (transaction["id"], checkid) }
                    subtrans["amount"] = b.find_element_by_id("icon%s"%(checkid)).text
                    if not subtrans["amount"].strip():
                        # Something gets wonky.  In this case, let's re-load the page and continue
                        b.find_element_by_link_text("Account Details").click()
                        common.scrolluntilclick(b,b.find_element_by_id("rtImg%i"%(loop)))
                        common.scrolluntilclick(b,b.find_element_by_id("ViewImages"))
                        subtrans["amount"] = b.find_element_by_id("icon%s"%(checkid)).text
                        if not subtrans["amount"].strip():
                            print "Warning: Empty transaction!"
                            subtrans["amount"] = "$0"
                    if common.scrolluntilclick(b,b.find_element_by_xpath("//td[@id='icon%s']/a/img"%(checkid))):
                        b.get(b.find_element_by_xpath("//td[@class='imageborder']/img").get_attribute("src"))
                        checkfn = subtrans["id"] + ".png"
                        files[checkfn] = b.get_screenshot_as_base64()
                        b.back()
                        subtrans["file"] = checkfn
                    newtransactions.append(subtrans)
        balance = b.find_element_by_class_name("module1bkgd13").text
        print "Balance %s %s" % (acct, balance)
        balances.append({"account": params["name"], "subaccount": acct, "balance": balance, "date": datetime.date.today()})
        b.find_element_by_link_text("Accounts Overview").click()
    b.find_element_by_link_text("Sign Off").click()
    time.sleep(2.5)
    b.close()
    return {"transactions": newtransactions, "balances": balances, "files": files}

if __name__ == "__main__":

    if len(sys.argv) < 2:
        sys.exit(1)

    params = { "state": "CA" }
    params["username"] = sys.argv[1]
    params["lastcheck"] = datetime.date.today()-datetime.timedelta(days=14)
    params["seenids"] = []
    data = downloadaccount(params)
    json.dump(data, open("bofa.json","w"), indent=2, default=str)
