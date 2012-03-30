import time
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
            b.execute_script("document.body.scrollTop=document.body.scrollTop+20;")
            time.sleep(0.1)

parsedate = lambda x: datetime.datetime.strptime(x,"%Y-%m-%d").date()
