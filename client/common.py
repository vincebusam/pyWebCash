import time
import datetime

def scrolluntilclick(b,e):
    for retry in range(80):
        try:
            e.click()
            return True
        except:
            b.execute_script("document.body.scrollTop=document.body.scrollTop+20;")
            time.sleep(0.1)

splitdate = lambda x: map(int,x.split("-"))
parsedate = lambda x: datetime.date(splitdate(x)[0],splitdate(x)[1],splitdate(x)[2])

