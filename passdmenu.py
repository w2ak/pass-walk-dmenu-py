#!/usr/bin/env python3
import argparse as ap
import yaml
import logging, sys, time, os, glob, shutil, subprocess, functools
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
                            input=input.encode('utf-8'),
                            check=check,
                            stdout=subprocess.PIPE)
    output = result.stdout.decode('utf-8')
    if check:
        return output
    else:
        return output, result.returncode

def justrun(args, input='', check=True):
    result = subprocess.run(args,
                            input=input.encode('utf-8'),
                            check=check)
    return result.returncode

def parse_args():
    p = ap.ArgumentParser(description='Helps you get some password from your\
            password-store. Then it either copies it to the clipboard\
            or directly types it where your cursor is.')
    p.add_argument('-v', '--verbose', dest='verb',
                    action='count', default=0,
                    help='increase verbosity')
    p.add_argument('-l', '--log-file', dest='log',
                    type=ap.FileType('w'), default=sys.stderr,
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
    return a

def merge_duplicates_constructor(loader, node, deep=False):
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        value = loader.construct_object(value_node, deep=deep)
        if key in mapping:
            if not isinstance(mapping[key],list):
                mapping[key] = [ mapping[key] ]
            mapping[key].append(value)
        else:
            mapping[key] = value
    return mapping
yaml.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
                    merge_duplicates_constructor)

@functools.cmp_to_key
def field_cmp(x, y):
    if x == "password":
        return -1
    if y == "password":
        return 1
    if x == "username":
        return -1
    if y == "username":
        return 1
    if x < y:
        return -1
    if x > y:
        return 1
    return 0

def getkeys_dict(d):
    return list(d)

def getchoices_dictkeys(d,k):
    return sorted(list(map(str,k)), key=field_cmp)

def getkeys_list(l):
    return list(range(len(l)))

def getchoices_listkeys(l,k):
    return list(map(lambda x: '#{:d} ({:})'.format(x,str(l[x])[:10]),k))

"""
Get binary paths.
"""
bin_sed = which('sed')
bin_pass = which('pass')
bin_dmenu = which('dmenu')
bin_xclip = which('xclip')
bin_xdotool = which('xdotool')

def dmenu_choice(choices, prefix=''):
    cmd_dmenu = [ bin_dmenu, '-p', prefix ]
    choice = getoutput(cmd_dmenu, input='\n'.join(choices))
    try:
        return choices.index(choice)
    except ValueError:
        return None

def walk_object(o, prefixes=list(),getkeys=list,
        getchoices=lambda y,x: list(map(str,x))):
    keys = getkeys(o)
    if len(keys)<1:
        return o
    if len(keys)==1:
        key = keys[0]
        prefixes.append(key)
        return walk(o[key],prefixes=prefixes)
    prefix = '.'.join(map(str,prefixes+['']))
    choices = getchoices(o,keys)
    index = dmenu_choice(choices, prefix=prefix)
    return None if index is None else walk(o[keys[index]])

def walk(o, prefixes=list()):
    if isinstance(o,dict):
        return walk_object(o, prefixes=prefixes,
                getkeys=getkeys_dict, getchoices=getchoices_dictkeys)
    if isinstance(o,list):
        return walk_object(o, prefixes=prefixes,
                getkeys=getkeys_list, getchoices=getchoices_listkeys)
    return o

def parse_pass_contents(contents):
    sedscript = "1 s/^(.*)$/password: \"\\1\"/; 2,$ s/^(.*): ([^-].*)$/\\1: \"\\2\"/; /^otpauth/ s/^/otpauth: /;"
    cmd_sed = [ bin_sed, '-r', sedscript ]
    result = getoutput(cmd_sed, input=contents)
    yobj = yaml.load(result)
    return yobj

if __name__=='__main__':
    args = parse_args()

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

    """
    Get password file contents.
    """
    cmd_pass = [ bin_pass, entry ]
    content = getoutput(cmd_pass)
    lg.info("Password file contents stored.")
    content = parse_pass_contents(content)
    lg.info("Password file contents parsed.")

    """
    Get desired value.
    """
    value = walk(content)
    lg.info("Desired value obtained.")

    """
    Output the value.
    """
    if args.type:
        cmd_type = [ bin_xdotool, 'type', '--clearmodifiers', '--file', '-' ]
        justrun(cmd_type, input=value)
        lg.info("Secret typed in window.")
    else:
        cmd_xclip = [ bin_xclip, '-i', '-selection', 'clipboard' ]
        justrun(cmd_xclip, input=value)
        lg.info("Secret copied to clipboard.")
