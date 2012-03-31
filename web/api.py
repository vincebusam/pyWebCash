#!/usr/bin/python
import os
import sys
import cgi
import time
import json
import random
import string
import Cookie
import urlparse
import datetime

sys.path.append("../db")
sys.path.append("../")

import config
import db
import aesjsonfile

def json_print(obj, header=None):
    print "Content-type: application/json"
    if header:
        print header
    outstr = json.dumps(obj, indent=2)
    print "Content-length: %s" % (len(outstr)+1)
    print
    print outstr
    sys.stdout.close()

def exit_error(code, message):
    print "Status: %s" % (code)
    print "Content-type: application/json"
    print
    print json.dumps({"error":message})
    sys.exit(0)

form = cgi.FieldStorage()
query = urlparse.parse_qs(os.getenv("QUERY_STRING") or "")

action = form.getfirst("action")
username = form.getfirst("username")
password = form.getfirst("password")

if action == "newuser":
    try:
        if username and password:
            json_print(db.create_db(username, password));
            sys.exit(0)
        else:
            exit_error(400, "Incomplete username/password")
    except Exception, e:
        exit_error(500, "Couldn't create new user " + e)
elif action == "getbanks":
    json_print(config.banks)
    sys.exit(0)

sessionfn = None
if os.getenv("HTTP_COOKIE"):
    try:
        cookies = Cookie.SimpleCookie()
        cookies.load(os.getenv("HTTP_COOKIE"))
        sessionfn = "%s/%s.json" % (config.sessiondir, cookies["sessionid"].value)
        if os.path.exists(sessionfn) and os.path.getmtime(sessionfn) < (time.time()-config.sessiontimeout):
            os.remove(sessionfn)
        if not os.path.exists(sessionfn):
            if (not username or not password):
                exit_error(403, "Session Expired")
            else:
                sessionfn = None
        else:
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
    if sessionfn:
        os.remove(sessionfn)
    exit_error(400,"incomplete username/password")

try:
    mydb = db.DB(username, password)
except Exception, e:
    if sessionfn:
        os.remove(sessionfn)
    exit_error(403,"Bad password: %s" % (e))

if action == "checklogin":
    json_print(True)
    sys.exit(0)

if sessionfn:
    os.utime(sessionfn, None)

if action == "login":
    cookies = Cookie.SimpleCookie()
    session = { "username": username, "password": password }
    cookies["sessionid"] = ''.join(random.choice(string.ascii_letters + string.digits) for x in range(32))
    cookies["sessionid"]["secure"] = True
    cookies["sessionid"]["path"] = os.path.dirname(os.getenv("REQUEST_URI") or "/")
    cookies["sessionkey"] = ''.join(random.choice(string.ascii_letters + string.digits) for x in range(32))
    cookies["sessionkey"]["secure"] = True
    cookies["sessionid"]["path"] = os.path.dirname(os.getenv("REQUEST_URI") or "/")
    sessionfn = "%s/%s.json" % (config.sessiondir, cookies["sessionid"].value)
    aesjsonfile.dump(sessionfn, session, cookies["sessionkey"].value)
    json_print(True, cookies)
    mydb.backup()
elif action == "logout":
    if sessionfn and os.path.exists(sessionfn):
        os.remove(sessionfn)
    expire = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%a, %d-%b-%Y %H:%M:%S PST")
    cookies = Cookie.SimpleCookie()
    cookies["sessionid"] = ""
    cookies["sessionid"]["expires"] = expire
    cookies["sessionid"]["path"] = os.path.dirname(os.getenv("REQUEST_URI") or "/")
    cookies["sessionkey"] = ""
    cookies["sessionkey"]["expires"] = expire
    cookies["sessionid"]["path"] = os.path.dirname(os.getenv("REQUEST_URI") or "/")
    json_print(True, cookies)
    mydb.backup()
elif action == "newtransactions":
    try:
        data = json.loads(form.getfirst("data"))
    except Exception, e:
        exit_error(400, "Bad transactions: %s %s" % (e, form.getfirst("data")[:20]))
    json_print(mydb.newtransactions(data))
elif action == "accountstodo":
    json_print(mydb.accountstodo())
elif action == "accounts":
    json_print(mydb.accounts())
elif action == "search":
    try:
        json_print(mydb.search(json.loads(form.getfirst("query") or "{}"),
                               form.getfirst("startdate") or "0",
                               form.getfirst("enddate") or "9",
                               int(form.getfirst("limit") or 100),
                               int(form.getfirst("skip") or 0)))
    except Exception, e:
        exit_error(400, "Bad search: %s" % (e))
elif action == "updatetransaction":
    try:
        data = json.loads(form.getfirst("data") or "{}")
        if not data:
            exit_error(400, "Bad transactions: no data")
    except Exception, e:
        exit_error(400, "Bad transactions: %s %s" % (e, form.getfirst("data")[:20]))
    json_print(mydb.updatetransaction(form.getfirst("id"), data, save=True))
elif action == "image" or query.get("image"):
    img = mydb.getimage(form.getfirst("id") or query["image"][0])
    if img:
        print "Content-type: image/png"
        print "Content-length: %s" % (len(img))
        print
        print img
    else:
        exit_error(404, "Image not found")
elif action == "editaccount":
    try:
        json_print(mydb.editaccount(json.loads(form.getfirst("account"))))
    except Exception, e:
        exit_error(400, "Bad account %s" % (e))
elif action == "getcategories":
    try:
        json_print(mydb.getcategories())
    except Exception, e:
        exit_error(500, "Error %s" % (e))
elif action == "getcenters":
    json_print(mydb.getcenters())
else:
    exit_error(404,"Method not found")
