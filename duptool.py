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
        log_dir = home

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
        status = __backup__(config_file,group)
        streamHandler.flush()
        logStream.flush()
        __send_mail__(config_file,status,logStream)
    else:
        logging.debug('Performing restore...')

#    rootLogger.removeHandler(streamHandler)
#    print logStream.getvalue()
#
def __backup__(config_file,group=None):
    json_data=open(config_file).read()
    config = json.loads(json_data)

    env_var = os.environ.copy()
    env_var['PASSPHRASE'] = config['encryption_key']


    groups = config['groups']
    if group is not None:
        if group in [g['name'] for g in groups]:
            groups = [g for g in groups if g['name'] == group]
        else:
            err_msg = "No such group %s in config" % group
            print err_msg
            logging.error(err_msg)
            exit(-100)
    global_status = True
    for g in groups:
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
        CMD.append(g['source_dir'])
        CMD.append(g['dest_dir'])
        if config.has_key('tmp_dir'):
            CMD.append('--tempdir')
            CMD.append(config['tmp_dir'])
        logging.debug('CMD: %s' % CMD)
        p = subprocess.Popen(CMD,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env_var)
        (stdout,stderr) = p.communicate()
        ret_code = p.returncode
        status &= ret_code == 0
        logging.info('Duplicity backup finished with code: %d' % ret_code)
        logging.info(stdout)
        logging.info(stderr)
        #Verifying backup
        VERIFY_CMD = ['duplicity','verify',g['dest_dir'],g['source_dir']]
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
    return global_status

def __send_mail__(config_file, status, logStream):
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

if __name__ == "__main__":
    main()
