# Client uses HTTP API
import os
import sys
import json
import urllib
import urllib2
import cookielib

sys.path.append((os.path.dirname(__file__) or ".") + "/../")

import config

cj = cookielib.CookieJar()

def callapi(action, postdata={}):
    postdata.update({"action": action})
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
    opener.addheaders = [("User-Agent", "pyWebCash Scraper")]
    f = opener.open(config.apiurl,urllib.urlencode(postdata))
    data = f.read()
    return json.loads(data)
