__author__ = 'michal'

import argparse
import os
import json
import subprocess
from urlparse import urlparse
import logging
import datetime
import StringIO
import smtplib
from email.mime.text import MIMEText

LOG_LEVEL = logging.DEBUG



def main():
    parser = argparse.ArgumentParser(description="A duplicity helper for backups.")
    parser.add_argument('-c','--config',help='Config file location.')
    parser.add_argument('-g','--group',help='Group name.')
    parser.add_argument('-l','--log_dir',help='Directory to save log file.')
    parser.add_argument('-r','--dry_run',help='Dry run w/o making actual action',action="store_true")
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

    if args.log_dir:
        log_dir = args.log_dir
    else:
        home = os.path.expanduser("~")
        log_dir = os.path.join(home,'.duptool')

    rootLogger = logging.getLogger()
    rootLogger.setLevel(LOG_LEVEL)
    log_file_name = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    logFormatter = logging.Formatter(logging.BASIC_FORMAT)

    fileHandler = logging.FileHandler("{0}/{1}.log".format(log_dir, log_file_name))
    fileHandler.setFormatter(logFormatter)
    fileHandler.setLevel(LOG_LEVEL)
    rootLogger.addHandler(fileHandler)

    logStream = StringIO.StringIO()
    streamHandler = logging.StreamHandler(logStream)
    streamHandler.setFormatter(logFormatter)
    streamHandler.setLevel(LOG_LEVEL)
    rootLogger.addHandler(streamHandler)

    logging.debug('Config file: %s' % config_file)
    logging.debug('Processing %s group(s)' % (group if group is not None else 'all'))

    if args.subparser_name == 'backup':
        logging.debug('Performing backup...')
        status = __backup__(config_file,group,args.dry_run)
        streamHandler.flush()
        logStream.flush()
        __send_mail__(config_file,status,logStream,args.dry_run)
    else:
        logging.debug('Performing restore...')

#    rootLogger.removeHandler(streamHandler)
#    print logStream.getvalue()
#
def __backup__(config_file,group=None,dry_run=False):
    json_data=open(config_file).read()
    config = json.loads(json_data)

    env_var = os.environ.copy()
    env_var['PASSPHRASE'] = config['encryption_key']


    groups = config['groups']
    if group is not None:
        if group in [g['name'] for g in groups]:
            groups = [g for g in groups if g['name'] == group]
            del groups[0]['auto_run']
        else:
            err_msg = "No such group %s in config" % group
            print err_msg
            logging.error(err_msg)
            exit(-100)
    global_status = True
    for g in [gr for gr in groups if not gr.has_key('auto_run') or gr['auto_run'] == True]:
        status = True
        logging.info("Backing up %s" % g['name'])
        if not os.path.exists(urlparse(g['dest_dir']).path):
            err_msg = '[Error] no dest dir %s' % g['dest_dir']
            print err_msg
            logging.error(err_msg)
            status = False
            continue
        #Backup
        CMD =  ['duplicity']
        CMD.extend(g['duplicity_opts'])
        if g.has_key('vol_size'):
            CMD.append('--volsize')
            CMD.append(g['vol_size'])
        if g.has_key('filter'):
            CMD.extend([e for t in map(__create_filter_cmd__,g['filter']) for e in t])
        CMD.append(g['source_dir'])
        CMD.append(g['dest_dir'])
        if config.has_key('tmp_dir'):
            CMD.append('--tempdir')
            CMD.append(config['tmp_dir'])
        logging.debug('CMD: %s' % " ".join([c for c in CMD]))
        if dry_run:
            return False
        p = subprocess.Popen(CMD,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env_var)
        (stdout,stderr) = p.communicate()
        ret_code = p.returncode
        status &= ret_code == 0
        logging.info('Duplicity backup finished with code: %d' % ret_code)
        logging.info(stdout)
        logging.info(stderr)
        #Verifying backup
        if g.has_key('verify') and g['verify'] == True:
            VERIFY_CMD = ['duplicity','verify']
            if g.has_key('filter'):
                VERIFY_CMD.extend([e for t in map(__create_filter_cmd__,g['filter']) for e in t] )
            VERIFY_CMD.append(g['dest_dir'])
            VERIFY_CMD.append(g['source_dir'])
            if config.has_key('tmp_dir'):
                VERIFY_CMD.append('--tempdir')
                VERIFY_CMD.append(config['tmp_dir'])
            p = subprocess.Popen(VERIFY_CMD,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env_var)
            (stdout,stderr) = p.communicate()
            ret_code = p.returncode
            status &= ret_code == 0
            logging.info('Duplicity verify finished with code: %d' % ret_code)
            logging.info(stdout)
            logging.info(stderr)
        #Clean up command
        if g.has_key('clean_cmd'):
            CLEAN_CMD = ['duplicity']
            CLEAN_CMD.extend(g['clean_cmd'])
            CLEAN_CMD.append(g['dest_dir'])
            if config.has_key('tmp_dir'):
                CLEAN_CMD.append('--tempdir')
                CLEAN_CMD.append(config['tmp_dir'])
            p = subprocess.Popen(CLEAN_CMD,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env_var)
            (stdout,stderr) = p.communicate()
            ret_code = p.returncode
            status &= ret_code == 0
            logging.info('Duplicity clean up finished with code: %d' % ret_code)
            logging.info(stdout)
            logging.info(stderr)
        #Whole group process status
        result_msg = 'SUCESS' if status else 'FAILED'
        logging.info('Backing up %s %s' % (g['name'], result_msg))
        logging.info('==========================================')
        global_status &= status

    for g in [gr for gr in groups if not gr.has_key('auto_run') or gr['auto_run'] == True]:
        if g.get('glacier'):
            glacier_sync(urlparse(g['dest_dir']).path, g['name'],
                prefix=g['name'], conf=config['glacier'])

    return global_status

def __create_filter_cmd__(filter_val):
    key = filter_val.keys()[0]
    return ['--' + key,filter_val[key]]

def __send_mail__(config_file, status, logStream,dry_run=False):
    if dry_run:
        return
    json_data=open(config_file).read()
    config = json.loads(json_data)
    if config.has_key('mail'):
        mail_cfg = config['mail']
        msg = MIMEText(logStream.getvalue())
        status_txt = 'SUCCESS' if status else 'FAILURE'
        msg['Subject'] = '%s backup' % status_txt
        msg['From'] = 'Duptool'
        msg['To'] = mail_cfg['to']
        s = smtplib.SMTP(mail_cfg['smtp_server'],587)
        s.ehlo()
        s.starttls()
        s.ehlo()
        s.login(mail_cfg['login'],mail_cfg['password'])
        s.sendmail('Duptool', [mail_cfg['to']], msg.as_string())
        s.quit()


def __get_home__():
    home = os.path.expanduser("~")
    conf_dir = os.path.join(home,'.duptool')
    if not os.path.exists(conf_dir):
        os.mkdir(os.path.join(home,'.duptool'))
    return os.path.join(conf_dir,'config.json')

def glacier_sync(folder, vault, prefix=None, conf=None, dry_run=False):
    import glacier_cli.glacier as gl
    import re
    import time

    delete_period = 35 * 24 * 60 * 60 ## 35 days in seconds after that delete
                                      # from glacier is free

    default_args = []
    if conf is not None:
        os.environ['AWS_ACCESS_KEY_ID'] = conf['aws_id']
        os.environ['AWS_SECRET_ACCESS_KEY'] = conf['aws_secret']
        if conf.get('aws_region'):
            default_args.extend(['--region', conf['aws_region']])
    if prefix is None:
        prefix = folder

    content = os.listdir(folder)
    files = set(unicode(f) for f in content if os.path.isfile(os.path.join(folder, f)))

    app = gl.App(args=['archive', 'list', '--detailed', vault], quiet=True)
    archives = app.args.func()
    to_sync = files - set(re.search(r'^(\[.*\])*[\ ]?(\S+)', a.name).groups()[1] for a in archives)

    for f in to_sync:
        args = ['archive', 'upload', '--name', '[%s] %s' % (prefix, f), vault, os.path.join(folder, f)]
        args.extend(default_args)
        if dry_run:
            logging.debug(args)
        else:
            app = gl.App(args=args, quiet=True)
            archive_id = app.args.func()
            logging.info('%s uploaded to Glacier with id: %s' % (f, archive_id))

    to_delete = set(a.name for a in archives if (time.time() - a.created_here) > delete_period) \
                - set('[%s] %s' % (prefix, f) for f in files)
    for a in to_delete:
        args = ['archive', 'delete', vault, a]
        args.extend(default_args)
        if dry_run:
            logging.debug(args)
        else:
            app = gl.App(args=args, quiet=True)
            app.args.func()
            logging.info('%s removed from Glacier.' % a)

if __name__ == "__main__":
    main()
