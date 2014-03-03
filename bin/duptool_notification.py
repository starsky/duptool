__author__ = 'michal'

from os.path import expanduser
from os.path import join
import os
from datetime import datetime
import pynotify
import duptool


def main():
    default_log_dir = join(expanduser("~"), '.duptool')
    log_files = filter(lambda x: 'log' in x, os.listdir(default_log_dir))
    log_files = filter(lambda x: x.startswith("SUCCESS"), log_files)
    log_files = map(lambda x: x.replace("SUCCESS_", ""), log_files)
    log_files.sort()
    if len(log_files) > 0:
        log_file_date_str = log_files[0].split('.')[0]
        log_datetime = datetime.strptime(log_file_date_str, '%Y%m%d%H%M%S')
        diff = datetime.now().date() - log_datetime.date()
        diff_threshold = 7
        if diff.days > diff_threshold:
            icon_path = os.path.join(os.path.dirname(os.path.realpath(duptool.__file__)), 'dialog-important-2.png')
            print icon_path
            pynotify.init("DUPTOOL")
            notice = pynotify.Notification('Backup reminder',
                                           'You missed your backup in %d days. Dummy!' % diff.days,
                                           icon_path)
            notice.set_urgency(pynotify.URGENCY_NORMAL)
            notice.show()


if __name__ == "__main__":
    main()