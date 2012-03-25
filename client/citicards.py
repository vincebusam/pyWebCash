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

def downloadaccount(params):
    if "password" not in params:
        params["password"] = getpass.getpass("Citi Credit Cards Password: ")
    b = webdriver.Chrome()
    b.get("https://creditcards.citi.com/")
    b.find_element_by_id("id").send_keys(params["username"])
    b.find_element_by_id("pw").send_keys(params["password"])
    b.find_element_by_class_name("login-submit").click()
    cards = [x.text for x in b.find_elements_by_class_name("card_info")]
    for card in cards:
        b.find_element_by_link_text(card).click()
        if not b.find_elements_by_class_name("curr_balance"):
            b.back()
            continue
        balance = b.find_element_by_class_name("curr_balance").text
        if balance == "$0.00":
            b.back()
            continue
        [x.click() for x in b.find_elements_by_class_name("activator")]
        for entry in b.find_elements_by_xpath("//table[@id='transaction-details-detail']//tbody"):
            print entry.text
        Select(b.find_element_by_id("date-select")).select_by_value("1")
        b.find_elements_by_xpath("//table[@id='transaction-details-search']//input")[-1].click()
        time.sleep(4)
        [x.click() for x in b.find_elements_by_class_name("activator")]
        for entry in b.find_elements_by_xpath("//table[@id='transaction-details-detail']//tbody"):
            print entry.text
        b.back()

if __name__ == "__main__":

    if len(sys.argv) < 2:
        sys.exit(1)

    params = {}
    params["username"] = sys.argv[1]
    params["lastcheck"] = datetime.date.today()-datetime.timedelta(days=14)
    params["seenids"] = []
    data = downloadaccount(params)
    json.dump(data, open("citicards.json","w"), indent=2, default=str)
