#!/usr/bin/python
import os
import sys
import json
import base64
import cPickle
from Crypto.Cipher import AES

BLOCK_SIZE = 32
PADDING = ' '
pad = lambda s: s + (BLOCK_SIZE - ((len(s) % BLOCK_SIZE) or BLOCK_SIZE)) * PADDING
EncodeAES = lambda c, s: base64.b64encode(c.encrypt(pad(s)))
DecodeAES = lambda c, e: c.decrypt(base64.b64decode(e)).rstrip(PADDING)

def load(fn, passwd):
    if len(passwd) > BLOCK_SIZE:
        raise Exception("Password too long")
    f = open(fn,"r")
    data = f.read()
    f.close()
    return cPickle.loads(AES.new(pad(passwd)).decrypt(base64.b64decode(data)).rstrip(PADDING))

def dump(fn, obj, passwd):
    if len(passwd) > BLOCK_SIZE:
        raise Exception("Password too long")
    data = base64.b64encode(AES.new(pad(passwd)).encrypt(pad(cPickle.dumps(obj,-1))))
    f = open(fn, "w")
    f.write(data)
    f.close()

def enc(data, passwd):
    return AES.new(pad(passwd)).encrypt(pad(data))

def dec(data, passwd):
    return AES.new(pad(passwd)).decrypt(data).rstrip(PADDING)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print "Usage: %s filename password <json update>" % (sys.argv[0])
        sys.exit(1)
    fn = sys.argv[1]
    passwd = sys.argv[2]
    obj = {}
    if os.path.exists(fn):
        try:
            obj = load(fn, passwd)
        except ValueError:
            print "Incorrect password or corrupt file"
            sys.exit(1)
    if len(sys.argv) > 3:
        if os.path.exists(sys.argv[3]):
            obj.update(json.load(open(sys.argv[3])))
        else:
            obj.update(json.loads(sys.argv[3]))
        dump(fn, obj, passwd)
    print json.dumps(obj, indent=2)
