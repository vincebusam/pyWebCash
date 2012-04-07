#!/usr/bin/python
import sys
import csv
import json
import base64
import common
import getpass
import hashlib
import urllib2

cols = ["date", "desc", "amount", "center"]

def downloadaccount(b, params):
    params["lastcheck"] = common.parsedate(params.get("lastcheck", "2000-01-01"))
    params.setdefault("seenids", [])
    params.setdefault("name", "Cash")
    if params.get("username") and not params.get("password"):
        params["password"] = getpass.getpass("Password for %s at %s: " % (params["username"], params["url"]))
    request = urllib2.Request(params["url"])
    if params.get("username") and params.get("password"):
        request.add_header("Authorization", "Basic %s" % base64.encodestring('%s:%s' % (params["username"], params["password"])).replace('\n', ''))
    f = urllib2.urlopen(request)
    transactions = []
    for entry in csv.reader(f):
        trans = {}
        for i in range(len(cols)):
            trans[cols[i]] = entry[i]
        if common.parsedate(trans["date"]) < params["lastcheck"]:
            continue
        trans["id"] = "%s-%s-%s" % (trans["date"], params["name"], hashlib.sha1(str(entry)).hexdigest())
        trans["account"] = params["name"]
        trans["subaccount"] = ""
        if trans["id"] in params["seenids"]:
            continue
        transactions.append(trans)
    return {"transactions": transactions}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(1)
    data = downloadaccount(None, {"url": sys.argv[1]})
    json.dump(data, open("csvurl.json", "w"), indent=2, default=str)
