#!/usr/bin/python
import re
import sys
import time
import hashlib
import getpass
import datetime
from selenium import webdriver
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.keys import Keys

def generateid(t):
    return "bofa-%s-%s-%s" % (t["subaccount"],t["date"],hashlib.sha1(t["desc"]).hexdigest())

def scrolluntilclick(b,e):
    for retry in range(40):
        try:
            e.click()
            return True
        except:
            b.execute_script("document.body.scrollTop=document.body.scrollTop+20;")
            time.sleep(0.1)

datematch = re.compile("(\d{2})/(\d{2})/(\d{4})")

# Params - dict of username, password, state, date, seenids
def downloadaccount(params):
    # By default, we'll get all transactions since 2000!
    params.setdefault("lastcheck",datetime.date(2000,1,1))
    params.setdefault("seenids",[])
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
    for acct in accounts:
        b.find_element_by_id(acct).click()
        for loop in range(1000):
            transaction = {"account": "bankofamerica", "subaccount": acct}
            if not b.find_elements_by_id("row%s" % (loop)):
                break
            date = b.find_element_by_xpath("//tr[@id='row%s']/td[3]" % (loop)).text
            m = datematch.match(date)
            if not m:
                continue
            transaction["date"] = datetime.date(int(m.group(3)),int(m.group(1)),int(m.group(2)))
            if transaction["date"] < (params["lastcheck"]-datetime.timedelta(days=4)):
                break
            transaction["desc"] = b.find_element_by_xpath("//tr[@id='row%s']/td[4]" % (loop)).text.replace("\n","")
            transaction["amount"] = b.find_element_by_xpath("//tr[@id='row%s']/td[7]" % (loop)).text
            transaction["id"] = generateid(transaction)
            print transaction
            if transaction["id"] in params["seenids"]:
                print "Already have %s" % (transaction["id"])
                continue
            if scrolluntilclick(b,b.find_element_by_id("rtImg%i"%(loop))):
                for line in b.find_element_by_id("exptd%s"%(loop)).text.split("\n"):
                    if ":" in line:
                        transaction["attr_" + line.split(":")[0].strip()] = line.split(":")[1].strip()
            newtransactions.append(transaction)
            if b.find_elements_by_id("ViewImages"):
                b.find_element_by_id("ViewImages").click()
                for checkid in range(1,20):
                    if not b.find_elements_by_id("icon%s"%(checkid)):
                        continue
                    subtrans = {"account": "bankofamerica",
                                "subaccount": acct,
                                "parent": transaction["id"],
                                "date": transaction["date"],
                                "desc": "BofA Check Deposit",
                                "id": "%s-%s" % (transaction["id"], checkid) }
                    subtrans["amount"] = b.find_element_by_id("icon%s"%(checkid)).text
                    if not scrolluntilclick(b,b.find_element_by_xpath("//td[@id='icon%s']/a/img"%(checkid))):
                        continue
                    b.get(b.find_element_by_xpath("//td[@class='imageborder']/img").get_attribute("src"))
                    checkfn = subtrans["id"] + ".png"
                    b.save_screenshot(checkfn)
                    b.back()
                    subtrans["file"] = checkfn
                    print subtrans
        balance = b.find_element_by_class_name("module1bkgd13").text
        print "Balance %s %s" % (acct, balance)
        balances.append({"account": "bankofamerica", "subaccount": acct, "balance": balance, "date": datetime.date.today()})
        b.find_element_by_link_text("Accounts Overview").click()
    b.find_element_by_link_text("Sign Off").click()
    time.sleep(2.5)
    b.close()
    return {"transactions": newtransactions, "balances": balances}

if __name__ == "__main__":

    if len(sys.argv) < 2:
        sys.exit(1)

    params = { "state": "CA" }
    params["username"] = sys.argv[1]
    params["password"] = getpass.getpass()
    params["lastcheck"] = datetime.date.today()-datetime.timedelta(days=14)
    params["seenids"] = []
    downloadaccount(params)
