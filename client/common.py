import os
import time
import json
import urlparse
import datetime

try:
    import prctl
    prctl.prctl(prctl.DUMPABLE, 0)
except ImportError:
    pass

def scrolluntilclick(b,e):
    for retry in range(80):
        try:
            e.click()
            return True
        except:
            b.execute_script("window.scrollBy(0,20);")
            time.sleep(0.1)

parsedate = lambda x: datetime.datetime.strptime(x,"%Y-%m-%d").date()

# Run this here on import before starting threads to avoid strptime/thread problem
parsedate("2010-01-01")

def loadcookies(b, cookies):
    domain = urlparse.urlparse(b.current_url).netloc
    for cookie in cookies:
        if not domain.endswith(cookie["domain"]):
            continue
        try:
            b.add_cookie(cookie)
        except Exception, e:
            pass
    b.refresh()

def savecookies(b):
    cookies = json.load(open("cookies.json")) if os.path.exists("cookies.json") else []
    for cookie in b.get_cookies():
        if not cookie.get("expiry"):
            continue
        for oldcookie in cookies:
            if oldcookie["domain"] == cookie["domain"] and oldcookie["name"] == cookie["name"] and oldcookie["path"] == cookie["path"] and cookie["expiry"] > oldcookie.get("expiry"):
                oldcookie.update(cookie)
                break
        else:
            cookies.append(cookie)
    json.dump(cookies, open("cookies.json","w"), indent=2)
