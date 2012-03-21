#!/usr/bin/python2.6
import sys
import api
import getpass

print "Login"
print "Username: ",
username = sys.stdin.readline().strip()
password = getpass.getpass()

if not api.callapi("login",{"username": username, "password": password}):
    print "Login failed"
    sys.exit(1)

todo = api.callapi("accountstodo")
print todo

api.callapi("logout")
