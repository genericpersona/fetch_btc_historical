#!/usr/bin/env python2

# Imports
import argparse
import os
import sys

import requests

# Constants
URLS = sys.argv[1:]

def build_parser():
    parser = argparse.ArgumentParser()

if not URLS:
    # Write error if no URLs present
    sys.stderr.write('[Usage]: {} [URLs]+\n'.format(sys.argv[0]))
    #sys.stderr.write('URLS: {}\n'.format(sys.argv))
    sys.exit(1)
else:
    # Loop through and treat like URLs
    for url in URLS:
        fname = url.split('/')[-1]
        if os.path.exists(fname):
            continue
    
        try:
            r = requests.get(url, stream=True)
            with open(fname, 'wb') as f:
                for line in r.iter_lines():
                    f.write(bytes(line))
        except:
            sys.exit(1)

    # Exit successfully
    sys.exit()

