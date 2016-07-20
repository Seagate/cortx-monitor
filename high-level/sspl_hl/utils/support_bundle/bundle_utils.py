"""
It will contain all the utility functions used by the bundling
"""
# Do NOT modify or remove this copyright and confidentiality notice

# Copyright 2015 Seagate Technology LLC or one of its affiliates.
#
# The code contained herein is CONFIDENTIAL to Seagate Technology LLC.
# Portions may also be trade secret. Any use, duplication, derivation,
# distribution or disclosure of this code, for any reason, not expressly
# authorized in writing by Seagate Technology LLC is prohibited.
# All rights are expressly reserved by Seagate Technology LLC.
# __author__ = 'Bhupesh Pant'

# Third party
import tarfile
import os
import glob
import re
from plex.core.log import error
from sspl_hl.utils import common
from sspl_hl.utils.support_bundle import config


def is_bundle_dir(f_name):
    """Check if the file is the bundle directory.
    This involves two checks,
    1. The file should be a directory
    2. It should start with a given format
    """
    def matches_pattern(string):
        """Check if the string mathces the rexex pattern to match
        the directory naming standard
        """
        if re.search('(\\d{4}-\\d{2}-\\d{2}_\\d{2}-\\d{2}-\\d{2})', string):
            return True
        else:
            return False

    return os.path.isdir(
        os.path.join(config.BASE_BUCKET_PATH, f_name)
    ) and \
        matches_pattern(f_name)


def list_in_progress_bundles_files():
    """
    List in progress bundles.
    """
    return [z_file for z_file in os.listdir(config.BASE_BUCKET_PATH)
            if is_bundle_dir(z_file)]


def list_completed_bundle_files():
    """
    Return the list of bundle names.
    """
    return list_tar_files(config.BASE_BUCKET_PATH)


def get_bundle_info():
    """Get the list of the bundles,
    1. Collected, so far and
    2. In progress
     """
    return dict(
        completed=list_completed_bundle_files(),
        in_progress=list_in_progress_bundles_files()
    )


def list_tar_files(path):
    """
    Return the list of names of all the bundled tar files in
    the path.
    """
    def is_bundle_package(f_name):
        """Check if the file is the bundle tar bar"""
        return os.path.isfile(os.path.join(config.BASE_BUCKET_PATH, f_name))\
            and \
            tarfile.is_tarfile(os.path.join(config.BASE_BUCKET_PATH, f_name))
        #     z_file.find('.tar') != -1
    try:
        return [
            z_file for z_file in os.listdir(path) if is_bundle_package(z_file)]
    except OSError:
        return []


def get_bundle_path(target_path):
    """
    Return the bundle complete path, including name
    """
    if not os.path.exists(target_path):
        os.mkdir(target_path)
    bundle_file_name = '{}'.format(os.path.join(
        target_path,
        common.get_curr_datetime_str()))
    return bundle_file_name


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
            common.get_curr_datetime_str()))
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


def get_bundle_dir_config(dir_struct_info, nodes_list, bundle_name):
    """
    Returns the bundle directory structure in json
    {
    '20151127155650': {
                'nodes': {
                        'node_1': {

                        },
                        'node_2': {

                        },
                        'node_3': {

                        }
                    },
                'logs': {

                },
                'plex_logs': {

                }
           }
    }
    """
    if 'nodes' in dir_struct_info:
        node_dict = dir_struct_info['nodes']
        for node in nodes_list:
            node_dict[node] = {}
    bundle_base_dir_name = bundle_name
    dir_struct = dict()
    dir_struct[bundle_base_dir_name] = dir_struct_info
    return dir_struct


def create_bundle_structure(base_path, dir_info):
    """
    dir_info is the dict returned by get_bundle_dir_config()
    """
    try:
        create_dir(base_path, dir_info)
    except OSError:
        raise


def create_dir(base_path, dir_info):
    """
    Create recursive directories and subdirectories
    """
    for key in dir_info.keys():
        new_path = os.path.join(base_path, key)
        os.mkdir(new_path)
        create_dir(new_path, dir_info[key])
