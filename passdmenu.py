#!/usr/bin/env python3
import argparse as ap
import logging, sys, time
lg = logging.getLogger(__name__)

def parse_args():
    p = ap.ArgumentParser()
    p.add_argument('-v', '--verbose', dest='verb',
                    action='count', default=0,
                    help='Increase verbosity.')
    p.add_argument('-l', '--log-file', dest='log',
                    type=ap.FileType('a'), default=sys.stderr,
                    help='Log file.')
    a = p.parse_args()
    lglvl = logging.DEBUG if a.verb > 2 else   \
            logging.INFO if a.verb > 1 else    \
            logging.WARNING if a.verb > 0 else \
            logging.ERROR
    logging.basicConfig(stream=a.log, level=lglvl)
    if a.log is not p.get_default('log'):
        a.log.write("======== {:} =========".format(
                    time.asctime(time.localtime(time.time()))))
    return a

if __name__=='__main__':
    args = parse_args()
    lg.info("This is passdmenu version 0.")
    lg.info("No function is available yet.")
    lg.debug("This is a debug message. Yay.")
    lg.warning("Please be careful when using this development version!")
    lg.error("NotImplemented")
    print(args)
