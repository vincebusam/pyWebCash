#!/usr/bin/python
"""
Sends out an email reminder when account is inactive for too long.
Requires that db filename contains an email address.
Can be symlinked: ln -s username.pck user@example.com.pck
"""
import os
import sys
import time
import smtplib

sys.path.append((os.path.dirname(__file__) or ".") + "/..")

import config

for email in [x for x in os.listdir(config.dbdir) if "@" in x]:
    if os.path.getmtime(config.dbdir+"/"+email) < time.time()-(60*60*24*14):
        email = email.rstrip(".pck").rstrip(".json")
        server = smtplib.SMTP("localhost")
        message  = "From: %s\n" % (email)
        message += "To: %s\n" % (email)
        message += "Subject: Update financial records\n"
        message += "\n"
        message += "Accounts not updated in a while, go on back and re-update\n"
        server.sendmail(email, [email], message)
        server.quit()
