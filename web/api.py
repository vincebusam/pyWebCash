#!/usr/bin/python
import os
import sys
import cgi
import json
import Cookie
import datetime

sys.path.append("../db")
sys.path.append("../")

import config
import aesjsonfile

def exit_error(code,message):
    print "Status: %s" % (code)
    print "Content-type: application/json"
    print
    print json.dumps({"error":message})
    sys.exit(0)

form = cgi.FieldStorage()

action = form.getfirst("action")
username = form.getfirst("username")
password = form.getfirst("password")
if os.getenv("HTTP_COOKIE"):
    try:
        cookies = Cookie.SimpleCookie()
        cookies.load(os.getenv("HTTP_COOKIE"))
        if not username:
            username = cookies["username"].value
        if not password:
            password = cookies["password"].value
    except (Cookie.CookieError, KeyError):
        pass

if not username or not password:
    exit_error(400,"incomplete username/password")

try:
    db = aesjsonfile.load("%s/%s.json"%(config.dbdir,username),password)
except Exception, e:
    exit_error(403,"Bad password: %s" % (e))

if action == "login":
    cookies = Cookie.SimpleCookie()
    cookies["username"] = username
    cookies["password"] = password
    print "Content-type: application/json"
    print cookies
    print
    print json.dumps(True)
elif action == "logout":
    expire = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%a, %d-%b-%Y %H:%M:%S PST")
    cookies = Cookie.SimpleCookie()
    cookies["username"] = ""
    cookies["username"]["expires"] = expire
    cookies["password"] = ""
    cookies["password"]["expires"] = expire
    print "Content-type: application/json"
    print cookies
    print
    print json.dumps(True)
else:
    exit_error(404,"Method not found")
