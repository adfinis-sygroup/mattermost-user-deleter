# Mattermost user deleter

When an user is deleted in LDAP Mattermost marks the user in its DB as Deleted (which means effectively disabled and not deleted). The messages and the user are still preserved.

Mattermost currently (2019-09) does not offer the possibility to delete users via the API, this is only possible via the Mattermost CLI-Tool (`mattermost user delete <USER>`).

This Script which runs on a Mattermost-Node first checks the Mattermost database for disabled users, and if they are not found in LDAP, it deletes the user over the CLI-Tool.

The Script uses Mattermost-Config for connecting to the database and LDAP.


## Installation

### Script Installation

Prerequisites:
- EPEL Repository activated

Procedure:
- Install requirements:
```
yum install install mysql-connector-python python-ldap python-setuptools
```
- Install the Script:
```
git clone https://github.com/adfinis-sygroup/mattermost-user-deleter
cd mattermost-user-deleter
python setup.py install
```

### Activate Mattermost User deleter timer

```
systemctl enable mattermost-user-deleter.timer
```

## Usage

```
usage: mattermost-user-deleter [-h] --config CONFIG --mattermost-root
                               MATTERMOST_ROOT [--dry-run] [--debug]
```

- `--config` path to Mattermost `config.json` (normally `/opt/mattermost/config/config.json`)
- `--mattermost-root` path to Mattermost install root (normally `/opt/mattermost`)
- `--debug` is a flag to display debug output
- `--dry-run` if this flag is specified, only show what the script would delete instead of actually deleting the users
