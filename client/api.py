# Client uses HTTP API
import sys
import json
import urllib
import urllib2
import cookielib

sys.path.append("../")

import config

cj = cookielib.CookieJar()

def callapi(action, postdata={}):
    postdata.update({"action": action})
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
    f = opener.open(config.apiurl,urllib.urlencode(postdata))
    data = f.read()
    return json.loads(data)
