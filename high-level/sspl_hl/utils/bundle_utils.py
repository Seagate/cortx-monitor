#!/usr/bin/python
# -*- coding: utf-8 -*-

# Do NOT modify or remove this copyright and confidentiality notice

# Copyright 2015 Seagate Technology LLC or one of its affiliates.
#
# The code contained herein is CONFIDENTIAL to Seagate Technology LLC.
# Portions may also be trade secret. Any use, duplication, derivation,
# distribution or disclosure of this code, for any reason, not expressly
# authorized in writing by Seagate Technology LLC is prohibited.
# All rights are expressly reserved by Seagate Technology LLC.

"""
This module will handle the packing and bundling
"""
# Third party
import tarfile
import time
import os
import re
import glob
from plex.core.log import error


def list_bundle_files(path):
    """
        Return the list of names of all the bundled tar files.
    """
    return [z_file for z_file in os.listdir(path) if re.match(
        r'[0-9]+.tar.gz', z_file)]


def get_curr_datetime_str():
    """
        Return current date time in yyyymmddhhmmss format.
    """
    time_st = time.localtime(time.time())
    date_time = "{}{}{}{}".format(
        time.strftime('%Y%m%d'),
        time_st.tm_hour,
        time_st.tm_min,
        time_st.tm_sec
    )
    return date_time


def bundle_files(target_files, target_path):
    """
        This function would be responsible for creating the tar ball of the
        selected files.
    """

    try:
        if not os.path.exists(target_path):
            os.mkdir(target_path)
        bundle_file_name = '{}.tar.gz'.format(os.path.join(
            target_path,
            get_curr_datetime_str()))
        bundle_file = tarfile.open(bundle_file_name, "w:gz")
        for files_to_bundle in target_files.itervalues():
            for file_pattern in files_to_bundle:
                matching_zfiles = glob.glob(file_pattern)
                for z_file in matching_zfiles:
                    bundle_file.add(z_file)
        bundle_file.close()
        return bundle_file_name
    except tarfile.TarError as extra_info:
        error(why=str(extra_info))
