__author__ = 'michal'

import argparse
import os
import json
import subprocess

def main():
    parser = argparse.ArgumentParser(description="A duplicity helper for backups.")
    parser.add_argument('-c','--config',help='Config file location.')
    parser.add_argument('-g','--group',help='Group name.')
    sub_parsers = parser.add_subparsers(dest='subparser_name')
    backup_parser = sub_parsers.add_parser('backup',help='preform backup')
    restore_parser = sub_parsers.add_parser('restore',help='preform restore')
    restore_parser.add_argument('location',help='Restore location.')
    args = parser.parse_args()

    if args.config:
        config_file = args.config
    else:
        config_file = __get_home__()

    if args.group:
        group = args.group
    else:
        group = None

    print config_file
    print 'Processing %s group(s)' % (group if group is not None else 'all')

    if args.subparser_name == 'backup':
        print 'Performing backup...'
        __backup__(config_file,group)
    else:
        print 'Performing restore...'

def __backup__(config_file,group=None):
    json_data=open(config_file).read()
    config = json.loads(json_data)
    groups = config['groups']
    if group is not None:
        if group in [g['name'] for g in groups]:
            groups = [g for g in groups if g['name'] == group]
        else:
            print "No such group %s in config" % group
            exit(-100)
    for g in groups:
        print "Backing up %s" % g['name']
        CMD =  ['duplicity']
        CMD.extend(g['duplicity_opts'])
        CMD.append(g['source_dir'])
        CMD.append(g['dest_dir'])
        print CMD
        p = subprocess.Popen(CMD, stdin=subprocess.PIPE)


def __get_home__():
    home = os.path.expanduser("~")
    conf_dir = os.path.join(home,'.duptool')
    if not os.path.exists(conf_dir):
        os.mkdir(os.path.join(home,'.duptool'))
    return os.path.join(conf_dir,'config.json')

if __name__ == "__main__":
    main()
