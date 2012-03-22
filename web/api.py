#!/usr/bin/python
import os
import sys
import cgi
import json
import random
import string
import Cookie
import datetime

sys.path.append("../db")
sys.path.append("../")

import config
import db
import aesjsonfile

def exit_error(code, message):
    print "Status: %s" % (code)
    print "Content-type: application/json"
    print
    print json.dumps({"error":message})
    sys.exit(0)

form = cgi.FieldStorage()

action = form.getfirst("action")
username = form.getfirst("username")
password = form.getfirst("password")
sessionfn = None
if os.getenv("HTTP_COOKIE"):
    try:
        cookies = Cookie.SimpleCookie()
        cookies.load(os.getenv("HTTP_COOKIE"))
        sessionfn = "%s/%s.json" % (config.sessiondir, cookies["sessionid"].value)
        if not os.path.exists(sessionfn):
            exit_error(403, "Session Expired")
        try:
            session = aesjsonfile.load(sessionfn, cookies["sessionkey"].value)
        except:
            exit_error(403,"Bad Session Token: %s" (e))
        if not username:
            username = session["username"]
        if not password:
            password = session["password"]
    except (Cookie.CookieError, KeyError):
        pass

if not username or not password:
    exit_error(400,"incomplete username/password")

try:
    mydb = db.DB(username, password)
except Exception, e:
    exit_error(403,"Bad password: %s" % (e))

if action == "login":
    cookies = Cookie.SimpleCookie()
    session = { "username": username, "password": password }
    cookies["sessionid"] = ''.join(random.choice(string.ascii_letters + string.digits) for x in range(32))
    cookies["sessionkey"] = ''.join(random.choice(string.ascii_letters + string.digits) for x in range(32))
    sessionfn = "%s/%s.json" % (config.sessiondir, cookies["sessionid"].value)
    aesjsonfile.dump(sessionfn, session, cookies["sessionkey"].value)
    print "Content-type: application/json"
    print cookies
    print
    print json.dumps(True)
    sys.exit(0)
elif action == "logout":
    if sessionfn and os.path.exists(sessionfn):
        os.remove(sessionfn)
    expire = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%a, %d-%b-%Y %H:%M:%S PST")
    cookies = Cookie.SimpleCookie()
    cookies["sessionid"] = ""
    cookies["sessionid"]["expires"] = expire
    cookies["sessionkey"] = ""
    cookies["sessionkey"]["expires"] = expire
    print "Content-type: application/json"
    print cookies
    print
    print json.dumps(True)
    sys.exit(0)

print "Content-type: application/json"
print

if action == "accountstodo":
    print json.dumps(mydb.accountstodo(), indent=2)
else:
    exit_error(404,"Method not found")
