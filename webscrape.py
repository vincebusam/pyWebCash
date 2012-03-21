#!/usr/bin/python
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import *

username = ""
password = ""

b = webdriver.Chrome()
b.get("https://www.bankofamerica.com/")
b.find_element_by_id("id").send_keys(username)
Select(b.find_element_by_id("stateselect")).select_by_value("CA")
b.find_element_by_id("top-button").click()
b.find_element_by_id("tlpvt-passcode-input").send_keys(password)
b.find_element_by_name("confirm-sitekey-submit").click()
accounts = {}
for a in b.find_elements_by_xpath("//div[contains(@class,'image-account')]/a")
    accounts[a.get_attribute("id")] = a.get_attribute("href")
for acct in accounts:
    b.get(accounts[acct])
    for loop in range(1000):
        try:
            b.find_element_by_id("row%s" % (loop))
        except:
            break
        date = b.find_element_by_xpath("//tr[@id='row%s']/td[3]" % (loop)).text
        desc = b.find_element_by_xpath("//tr[@id='row%s']/td[4]" % (loop)).text
        amount = b.find_element_by_xpath("//tr[@id='row%s']/td[7]" % (loop)).text
        b.find_element_by_id("rtImg%i"%(loop)).click()
        b.find_element_by_id("ViewImages").click()
        for checkid in range(1,1000):
            try:
                b.find_element_by_id("icon%s"%(checkid)).text
            except:
                break
            b.find_element_by_xpath("//td[@id='icon%s']/a/img"%(checkid)).click()
            b.get(b.find_element_by_xpath("//td[@class='imageborder']/img").get_attribute("src"))
            b.save_screenshot("check.png")
