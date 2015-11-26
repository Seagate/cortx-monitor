"""
Contain the common utils and functions
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

import subprocess
import datetime


def execute_shell(shell_cmd):
    """
    Execute the command in shell
    """
    return subprocess.check_output(
        shell_cmd,
        stderr=subprocess.PIPE,
        shell=True
    )


def get_curr_datetime_str():
    """
        Return current date time in yyyymmddhhmmss format.
    """
    date_time = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    return date_time
