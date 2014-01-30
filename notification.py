__author__ = 'michal'

from os.path import expanduser
from os.path import join
import os
from datetime import datetime
import pynotify

def main():
    default_log_dir = join(expanduser("~"), '.duptool')
    log_files = filter(lambda x: 'log' in x, os.listdir(default_log_dir))
    log_files.sort()
    if len(log_files) > 0:
        log_file_date_str = log_files[0].split('.')[0]
        log_datetime = datetime.strptime(log_file_date_str, '%Y%m%d%H%M%S')
        diff = datetime.now().date() - log_datetime.date()
        diff_treshold = 7
        if diff.days > diff_treshold:
            icon_path = os.path.abspath('dialog-important-2.png')
            pynotify.init("DUPTOOL")
            notice = pynotify.Notification('Backup reminder',
                'You missed your backup in %d days. Dummy!' % diff_treshold,
                icon_path)
            notice.set_urgency(pynotify.URGENCY_NORMAL)
            notice.show()

if __name__ == "__main__":
    main()