#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import json
import logging
import argparse
import subprocess

import ldap
import mysql.connector


logger = logging.getLogger(__name__)



class MySQLCursorDict(mysql.connector.cursor.MySQLCursor):
    """assoc fetch for mysql.connect"""
    def _row_to_python(self, rowdata, desc=None):
        row = super(MySQLCursorDict, self)._row_to_python(rowdata, desc)
        if row:
            return dict(zip(self.column_names, row))
        return None


class ArgparseDirFullPaths(argparse.Action):
    """Expand user- and relative-paths"""
    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, os.path.abspath(os.path.expanduser(values)))


def argparse_is_dir(dirname):
    """Checks if a path is an actual directory"""
    if not os.path.isdir(dirname):
        msg = "{0} is not a directory".format(dirname)
        raise argparse.ArgumentTypeError(msg)
    else:
        return dirname


def setup_logging(debug=False):
    """Configure logging to stdout."""
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    stdout_handler = logging.StreamHandler(sys.stdout)

    stdout_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    stdout_handler.setLevel(logging.INFO)
    if debug:
        stdout_handler.setLevel(logging.DEBUG)
    stdout_handler.setFormatter(stdout_formatter)

    root.addHandler(stdout_handler)



class App:

    def __init__(self):
        """
        This function gets called when initing the class
        """
        pass


    def main(self):
        """
        Main function which controls the app
        """
        self.parse_args()
        setup_logging(self.args.debug)
        self.parse_config()
        self.connect_db()
        self.connect_ldap()
        self.delete_old_users()


    def parse_args(self):
        """
        parses the arguments passed to the script
        """
        parser = argparse.ArgumentParser(
            description="Mattermost user purger"
        )
        parser.add_argument(
            "--config",
            type=argparse.FileType("r"),
            required=True
        )
        parser.add_argument(
            "--mattermost-root",
            type=argparse_is_dir,
            action=ArgparseDirFullPaths,
            required=True
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            default=False
        )
        parser.add_argument(
            '--debug',
            action='store_true',
            default=False
        )
        self.args = parser.parse_args()


    def parse_config(self):
        """
        parses given mattermost config and extracts
        database and ldap connection
        """

        self.mm_config = json.load(self.args.config)

        # this part is pretty ugly but works for now
        sqlpath = self.mm_config['SqlSettings']['DataSource']
        self.db_user, self.db_pass = sqlpath.split('@')[0].split(":")
        self.db_host, self.db_port = sqlpath[sqlpath.find("(")+1:sqlpath.find(")")].split(":")
        self.db_name = sqlpath[sqlpath.find(")/")+2:sqlpath.find("?")]

        ldap_protocol = "ldap://"
        if self.mm_config['LdapSettings']['ConnectionSecurity'] == 'TLS':
            ldap_protocol = "ldaps://"
        self.ldap_server = "{0}{1}:{2}".format(
            ldap_protocol,
            self.mm_config['LdapSettings']['LdapServer'],
            self.mm_config['LdapSettings']['LdapPort'],
        )
        self.ldap_binduser = self.mm_config['LdapSettings']['BindUsername'].decode()
        self.ldap_bindpass = self.mm_config['LdapSettings']['BindPassword'].decode()
        self.ldap_basedn   = self.mm_config['LdapSettings']['BaseDN'].decode()

        # set mattermost cli path
        self.mm_cli_path = os.path.join(
            self.args.mattermost_root,
            "bin/mattermost"
        )


    def connect_db(self):
        """
        connects to the database and exits the app
        if something is wrong
        """
        try:
            self.db_connection = mysql.connector.connect(
                user=self.db_user,
                password=self.db_pass,
                host=self.db_host,
                port=self.db_port,
                database=self.db_name
            )
            self.db_cursor = self.db_connection.cursor(cursor_class=MySQLCursorDict)
        except:
            logger.error("cannot connect to database")
            sys.exit(1)

        logger.debug("connected database: {0}/{1} as user {2}".format(
            self.db_host,
            self.db_name,
            self.db_user
        ))


    def connect_ldap(self):
        """
        connects to the directory server and exits the app
        if something is wrong
        """
        try:
            self.ldap_connection = ldap.initialize(
                self.ldap_server
            )
            self.ldap_connection.simple_bind(
                self.ldap_binduser,
                self.ldap_bindpass
            )
        except:
            logger.error("cannot connect to LDAP")
            sys.exit(1)

        logger.debug("connected LDAP server: {0} as user {1}".format(
            self.ldap_server,
            self.ldap_binduser
        ))


    def delete_old_users(self):
        """
        this function does the actual deletion of users
        """

        # fetch list of all disabled users in mattermost
        self.db_cursor.execute("SELECT * FROM Users WHERE DeleteAt>0")
        delete_candidates = self.db_cursor.fetchall()

        # loop over all delete candidates
        for user in delete_candidates:

            # look up user in LDAP
            ldap_query = "uid={0}".format(user['AuthData'])
            logger.debug("user: {0} is a candidate, LDAP-search: {1}".format(
                user['Username'],
                ldap_query
            ))
            ldap_res = self.ldap_connection.search_s(
                self.ldap_basedn,
                ldap.SCOPE_SUBTREE,
                ldap_query
            )
            if ldap_res:
                logger.debug("user {0} exists in LDAP, skipping".format(
                    ldap_query
                ))
            else:
                logger.info("user {0} not found in LDAP, deleting".format(
                    ldap_query
                ))
                if not self.args.dry_run:
                    self.delete_mm_user(user)


    def delete_mm_user(self, user):
        """
        delete the user over the mattermost cli interface
        """

        logger.info("deleting user with ID {0}".format(
            user['Id']
        ))
        cmd = [
            self.mm_cli_path,
            "user",
            "delete",
            user['Id'],
            "--confirm"
        ]
        subprocess.check_output(cmd)




def main():
    app = App()
    app.main()

if __name__ == '__main__':
    main()
