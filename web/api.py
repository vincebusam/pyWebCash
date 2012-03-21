#!/usr/bin/python
import os
import sys
import cgi
import json
import Cookie

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
    cookies = Cookie.SimpleCookie()
    cookies.load(os.getenv("HTTP_COOKIE"))
    if not username:
        username = cookies["username"].value
    if not password:
        password = cookies["password"].value

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
else:
    exit_error(404,"Method not found")
