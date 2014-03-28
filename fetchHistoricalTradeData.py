#!/usr/bin/env python2

# Imports
import argparse
import datetime
import logging
from operator import itemgetter as ig
import os 
import subprocess
import sys
import time

from bs4 import BeautifulSoup as BS
import psutil
import requests

# Constants
HISTORICAL_BTC_URL = 'http://api.bitcoincharts.com/v1/csv/'

# Functions
def get_all_links():
    r = requests.get(HISTORICAL_BTC_URL)
    soup = BS(r.text)
    links = [HISTORICAL_BTC_URL + \
                link['href'] for link \
                  in soup.find_all('a') \
                  if not link['href'] \
                    in ('../',)]
    return links

def load_bar(i, n, secs, w=50):
    '''
    Print a status bar. Code from:

        http://ow.ly/v6j1l
    '''
    if (i != n) and (i % (n // 100) != 0):
        return

    ratio = i / float(n)
    c = int(ratio * w)
    rate = float(i) / float(secs)
    etr = (n - i) * rate

    # Calculate hours, minutes and seconds
    em, es = divmod(secs, 60)
    eh, em = divmod(em, 60)

    etrm, etrs = divmod(etr, 60)
    etrh, etrm = divmod(etrm, 60)

    sys.stdout.write('Elapsed: {h:01d}:{m:02d}:{s:02d} '.\
                        format(h=int(eh), m=int(em), s=int(es)))
    sys.stdout.write('{:3}% ['.format(int(ratio*100)))
    sys.stdout.write('='*c)
    sys.stdout.write(' '*(w-c))
    sys.stdout.write('] ETR: {h:01d}:{m:02d}:{s:02d}\r'.\
                            format(h=int(etrh), m=int(etrm), s=int(etrs)))
    sys.stdout.flush()

def parse_args():
    parser = argparse.ArgumentParser(\
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument( '-n'
                       , '--num-workers'
                       , help='Number of simultaneous workers ' + \
                              'to download data. Defaults to  ' + \
                              'the number of processors.'
                       , default=psutil.NUM_CPUS
                       , type=int 
                       )
    parser.add_argument( '--downloader'
                       , help='Path to downloader program which ' + \
                              'should take a URL and return a ' + \
                              'typical status code.'
                       , default=os.path.join(os.getcwd(), 'downloadFile.py')
                       )
    parser.add_argument( '--output-dir'
                       , help='Directory to save files to.' 
                       , default=os.path.join(os.getcwd(), 'gzips')
                       )
    return parser.parse_args()

if __name__ == '__main__':
    # Parse the arguments
    args = parse_args()

    # Get all links from the page
    links = get_all_links()

    # Set up some logging
    logging.basicConfig( filename='historyDL.log'
                       , level=logging.INFO
                       , format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s'
                       , filemode='w'
                       )

    # Create several forked processes 
    # to download all the links
    downloaded = set()
    children = []           # PIDs of children
    pid_to_link = {}        # Map PID to link, i.e., URL
    
    # Get into the directory for 
    # saving the data
    old_pwd = os.getcwd()
    if not os.path.isdir(args.output_dir):
        os.mkdir(args.output_dir)
    os.chdir(args.output_dir)

    # Save some data and begin
    start = time.time()
    total_links = len(links)
    successes = 0
    sys.stdout.write('Starting downloads w/ {} workers\n'.\
                                        format(args.num_workers))
    for i, link in enumerate(links):
        # Log what's happening
        logging.info('[DLing #{}]: {}'.format(i+1, link)) 

        # Check if we've maxed out the number of workers
        if len(children) == args.num_workers:
            # Potential TO DO:
            #   Re-add mistakes to pid_to_link 
            #   but avoid infinite loops
            pid_status = [os.waitpid(child, os.WNOHANG) \
                                        for child in children]

            # Only get children who have exited 
            pid_status = [pidt for pidt in pid_status \
                                            if pidt != (0, 0)]

            # Save successes
            success = len([pidt for pidt in pid_status \
                                            if pidt[-1] == 0])
            successes += success

            # Reset the number of children PIDs
            children = [pid for pid in children \
                        if pid in map(ig(0), pid_status)]

        # If not too many workers, fork and download
        pid = os.fork()

        # Check for the parent or child
        if pid:                         # Parent process
            # Store child's PID
            children.append(pid)
            pid_to_link[pid] = link

            # Print the progress bar
            load_bar(i+1, total_links, time.time()-start)
        else:
            # For children, exec into a new program
            # that just downloads the URL and 
            # returns a status code 
            os.execv(args.downloader, (args.downloader, link))

    # Change back to start dir
    os.chdir(old_pwd)

    # Print finish message
    sys.stdout.write('\n\tDownloaded {} out of {} files in {}\n'.\
        format(successes, total_links, 
            str(datetime.timedelta(seconds=time.time()-start))))
