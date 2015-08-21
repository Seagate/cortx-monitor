#!/usr/bin/python
# -*- coding: utf-8 -*-

""" File containing factory class implementation for the different
sub commands supported by cstpr command
"""

# Do NOT modify or remove this copyright and confidentiality notice

# Copyright 2015 Seagate Technology LLC or one of its affiliates.
#
# The code contained herein is CONFIDENTIAL to Seagate Technology LLC.
# Portions may also be trade secret. Any use, duplication, derivation,
# distribution or disclosure of this code, for any reason, not expressly
# authorized in writing by Seagate Technology LLC is prohibited.
# All rights are expressly reserved by Seagate Technology LLC.

# Import System Modules

import argparse

# Import Local Modules

from cstor.cli.commands.node import Node
from cstor.cli.commands.service import Service
from cstor.cli.commands.ha import Ha
from cstor.cli.commands.power import Power
from cstor.cli.commands.fru import FieldReplaceableUnit


class Factory(object):

    """ Factory implementation to make the main cstor script
    agnostic to what sub-command is being called. As per the
    sub-command the object corresponding to that sub-command
    will be created and sent back to the main cstor script
    """

    @staticmethod
    def parse_args():
        """ Defining argparser for the main cstor command and
        including the argparser for sub-commands as the subparser
        to the main parser.
        Parser for any new subcommand to be added, should be added here
        """
        parser = argparse.ArgumentParser(description='CStor CLI command')
        subparsers = parser.add_subparsers()
        Service.add_args(subparsers)
        Node.add_args(subparsers)
        Ha.add_args(subparsers)
        Power.add_args(subparsers)
        FieldReplaceableUnit.add_args(subparsers)
        args = parser.parse_args()
        return args

    @staticmethod
    def get_subcmd():
        """ Returns the object created for the subcommand
        which was invoked by the user through CLI
        """
        args = Factory.parse_args()
        return args.func(args)
