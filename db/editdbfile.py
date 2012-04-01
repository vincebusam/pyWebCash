#!/usr/bin/python
# Edit an AES encrypted json/pickle file.
import os
import sys
import json
import getpass
import tempfile
import subprocess
import aespckfile
import aesjsonfile

def editfile(fn, password):
    filetype = aespckfile
    if ".json" in fn:
        filetype = aesjsonfile
    db = filetype.load(fn, password)
    f = tempfile.NamedTemporaryFile()
    json.dump(db, f, indent=2)
    f.flush()
    while True:
        subprocess.call([os.getenv("EDITOR") or "editor", f.name])
        try:
            f.seek(0)
            db = json.load(f)
            filetype.dump(fn, db, password)
            break
        except Exception, e:
            print "Error in json"
            print e
            print "Try again (y/n)? ",
            input = raw_input()
            if not input.lower().startswith("y"):
                break
    f.seek(0,2)
    len = f.tell()
    f.seek(0)
    f.write(" " * len)
    f.flush()
    f.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(1)
    fn = sys.argv[1]
    password = getpass.getpass()
    editfile(fn, password)
