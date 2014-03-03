===========
DupTool
===========

DupTool provides convenient way to define and run your backup job using duplicity. In DupTool config file you can define named backup groups which can include different duplicity options. Later you can run each group simply by running duptool script and backup group name. DupTool also allows user to define file groups which can be used with different backup groups, for instance one backup group can include given file group, where different backup group can exculde given file group.
Below you can find example config file::

    {
        "file_groups": {
            "fg1" : ["/dir/a.txt", "/dir/b.txt"],
            "fg2" : ["/dir/c.txt", "/dir/d.txt"]
        },
        "groups":[
            {
                "name":"First Backup Group",
                "description" : "Description",
                "source_dir":"/dir/",
                "dest_dir":"file:///backup_destination",
                "filter": [{"include": "$fg1"},{"exclude": "**"}],
                "duplicity_opts": ["--full-if-older-than", "1M"],
                "clean_cmd": ["remove-all-but-n-full","1"]
            },
            {
                "name":"Second Backup Group",
                "description" : "Description",
                "source_dir":"/dir/",
                "dest_dir":"file:///second_destination",
                "filter": [{"exclude": "$fg1"}],
                "duplicity_opts": ["--full-if-older-than", "7D"],
                "clean_cmd": ["remove-all-but-n-full","1"],
                "auto_run" : true
            },
        ],
        "vol_size": "1G",
        "encryption_key":"SECRET_K
    }

In this example two File Groups are declared: **fg1** and **fg2**. And two Backup Groups, in first Backup Group files and directires only from **fg1** are backedup. Where in second Backup Group all files and directories EXCEPT from **fg1** are backed up.

In default scenario this config file should be placed in ~/.duptool/config.json.

This allow to run above backups using simple command: 

    duptool backup


Notification 
============

User can use duptool_notification to show notification bubble if backup was not done for certain days count.
User can simply add command::

    duptool_notification

to cron to check if there is a need of backup and if yes notification bubble will be shown in operating system


Duplicity
==========

Make sure that duplicity is installed on your operating system.
Instructions on instalation can be found on: http://duplicity.nongnu.org/
In Ubuntu or Debian like systems you can install it by::

    sudo apt-get install duplicity

