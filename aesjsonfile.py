#!/usr/bin/python2.6
import os
import sys
import json
import base64
from Crypto.Cipher import AES

BLOCK_SIZE = 32
PADDING = ' '
pad = lambda s: s + (BLOCK_SIZE - len(s) % BLOCK_SIZE) * PADDING
EncodeAES = lambda c, s: base64.b64encode(c.encrypt(pad(s)))
DecodeAES = lambda c, e: c.decrypt(base64.b64decode(e)).rstrip(PADDING)

def aesjsonload(fn,passwd):
    f = open(fn,"r")
    data = f.read()
    f.close()
    return json.loads(AES.new(pad(passwd)).decrypt(base64.b64decode(data)).rstrip(PADDING))

def aesjsondump(fn,obj,passwd):
    data = base64.b64encode(AES.new(pad(passwd)).encrypt(pad(json.dumps(obj))))
    f = open(fn,"w")
    f.write(data)
    f.close()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print "Usage: %s filename password <json update>" % (sys.argv[0])
        sys.exit(1)
    fn = sys.argv[1]
    passwd = sys.argv[2]
    obj = {}
    if os.path.exists(fn):
        obj = aesjsonload(fn,passwd)
    if len(sys.argv) > 3:
        obj.update(json.loads(sys.argv[3]))
        aesjsondump(fn,obj,passwd)
    print json.dumps(obj,indent=2)
