#!/usr/bin/env python3
import argparse as ap
import logging, sys, time, os, glob, shutil, subprocess
lg = logging.getLogger(__name__)

def failwith(rc, msg="Unspecified"):
    lg.error(msg)
    sys.exit(rc)

def which(prog):
    binex = shutil.which(prog)
    if binex is None:
        failwith(1, msg="Could not find executable for '{:}'!".format(prog))
    return binex

def getoutput(args, input='', check=True):
    result = subprocess.run(args,
                            input=input.encode('ascii'),
                            check=check,
                            stdout=subprocess.PIPE)
    output = result.stdout.decode('ascii')
    if check:
        return output
    else:
        return output, result.returncode

def parse_args():
    p = ap.ArgumentParser(description='Helps you get some password from your\
            password-store. Then it either copies it to the clipboard\
            or directly types it where your cursor is.')
    p.add_argument('-v', '--verbose', dest='verb',
                    action='count', default=0,
                    help='increase verbosity')
    p.add_argument('-l', '--log-file', dest='log',
                    type=ap.FileType('a'), default=sys.stderr,
                    metavar='<file>', help='log file')
    p.add_argument('-t', '--type', dest='type',
                    action='store_true', default=False,
                    help='type obtained value somewhere')
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
    """
    Get arguments and binary paths from PATH.
    """
    args = parse_args()
    bin_pass = which('pass')
    bin_dmenu = which('dmenu')

    """
    Get the password store directory from the environment.
    """
    prefix = os.path.expanduser('~/.password-store')
    prefix = os.getenv('PASSWORD_STORE_DIR', prefix)
    ext = '.gpg'
    lg.debug("Prefix:'{:}'".format(prefix))

    """
    Get the list of available passwords in the store.
    """
    iglob = os.path.join('**', '*' + ext)
    iglob = os.path.join(prefix, iglob)
    options = list()
    for filename in glob.iglob(iglob, recursive=True):
        passname = filename[1+len(prefix):-len(ext)]
        lg.debug("Option found:'{:}'".format(passname))
        options.append(passname)
    lg.info("Found {:d} options in password store.".format(len(options)))

    """
    Get database entry name.
    """
    cmd_dmenu = [ bin_dmenu ]
    entry,rc = getoutput(cmd_dmenu,
                        input='\n'.join(options),
                        check=False)
    if rc:
        failwith(rc,
                msg = "Database entry choice failed with rc {:d}.".format(rc))
    entry = entry.strip()
    lg.info("Chosen database entry:'{:}'".format(entry))
