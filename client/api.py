# Client uses HTTP API
import os
import sys
import json
import urllib
import httplib
import urllib2
import cookielib

sys.path.append((os.path.dirname(__file__) or ".") + "/../")

import config

cj = cookielib.CookieJar()

class HTTPSClientAuthHandler(urllib2.HTTPSHandler):
    def __init__(self, key):
        urllib2.HTTPSHandler.__init__(self)
        self.key = key

    def https_open(self, req):
        # Rather than pass in a reference to a connection class, we pass in
        # a reference to a function which, for all intents and purposes,
        # will behave as a constructor
        return self.do_open(self.getConnection, req)

    def getConnection(self, host, timeout=300):
        return httplib.HTTPSConnection(host, key_file=self.key, cert_file=self.key)

def callapi(action, postdata={}):
    postdata.update({"action": action})
    if config.certfile:
        opener = urllib2.build_opener(HTTPSClientAuthHandler(config.certfile), urllib2.HTTPCookieProcessor(cj))
    else:
        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
    opener.addheaders = [("User-Agent", "pyWebCash Scraper")]
    f = opener.open(config.apiurl,urllib.urlencode(postdata))
    data = f.read()
    return json.loads(data)
