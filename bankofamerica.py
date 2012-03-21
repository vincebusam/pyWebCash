#!/usr/bin/python
import re
import sys
import time
import getpass
import datetime
from selenium import webdriver
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.keys import Keys

def scrolluntilclick(b,e):
    for retry in range(40):
        try:
            e.click()
            return True
        except:
            b.execute_script("document.body.scrollTop=document.body.scrollTop+20;")
            time.sleep(0.1)

if len(sys.argv) < 2:
    sys.exit(1)

datematch = re.compile("(\d{2})/(\d{2})/(\d{4})")

# Params - dict of username, password, state, date, seenids
def downloadaccount(params):
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
    for acct in accounts:
        b.find_element_by_id(acct).click()
        for loop in range(1000):
            if not b.find_elements_by_id("row%s" % (loop)):
                break
            date = b.find_element_by_xpath("//tr[@id='row%s']/td[3]" % (loop)).text
            m = datematch.match(date)
            if not m:
                continue
            date = datetime.date(int(m.group(3)),int(m.group(1)),int(m.group(2)))
            if date < (params["lastcheck"]-datetime.timedelta(days=4)):
                break
            desc = b.find_element_by_xpath("//tr[@id='row%s']/td[4]" % (loop)).text.replace("\n","")
            amount = b.find_element_by_xpath("//tr[@id='row%s']/td[7]" % (loop)).text
            print "Transaction: %s %s %s %s" % (acct,date,desc,amount)
            if scrolluntilclick(b,b.find_element_by_id("rtImg%i"%(loop))):
                attrs = {}
                for line in b.find_element_by_id("exptd%s"%(loop)).text.split("\n"):
                    if ":" in line:
                        attrs[line.split(":")[0].strip()] = line.split(":")[1].strip()
                if attrs:
                    print attrs
                continue
            if b.find_elements_by_id("ViewImages"):
                b.find_element_by_id("ViewImages").click()
                for checkid in range(1,20):
                    if not b.find_elements_by_id("icon%s"%(checkid)):
                        continue
                    amount = b.find_element_by_id("icon%s"%(checkid)).text
                    print "Check %s %s" % (checkid, amount)
                    gotcheck = False
                    if not scrolluntilclick(b,b.find_element_by_xpath("//td[@id='icon%s']/a/img"%(checkid))):
                        continue
                    b.get(b.find_element_by_xpath("//td[@class='imageborder']/img").get_attribute("src"))
                    b.save_screenshot(("%s-%s-%s.png"%(acct,date,checkid)).replace("/","_"))
                    b.back()
        balance = b.find_element_by_class_name("module1bkgd13").text
        print "Balance %s %s" % (acct, balance)
        b.find_element_by_link_text("Accounts Overview").click()
    b.find_element_by_link_text("Sign Off").click()
    time.sleep(5)
    b.close()

if __name__ == "__main__":
    params = { "state": "CA" }
    params["username"] = sys.argv[1]
    #print "Enter password for %s: " % (params["username"]),
    params["password"] = getpass.getpass()
    params["lastcheck"] = datetime.date.today()-datetime.timedelta(days=14)
    params["seenids"] = []
    downloadaccount(params)
