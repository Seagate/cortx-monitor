#!/usr/bin/python3.6
# -*- coding: utf-8 -*-

# Copyright (c) 2001-2020 Seagate Technology LLC and/or its Affiliates
#
# This program is free software: you can redistribute it and/or modify it under the
# terms of the GNU Affero General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
# PARTICULAR PURPOSE. See the GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License along
# with this program. If not, see <https://www.gnu.org/licenses/>. For any questions
# about this software or licensing, please email opensource@seagate.com or
# cortx-questions@seagate.com.


"""
 ****************************************************************************
  Description:       Report free space as IEM to be sent back to Seagate periodically via RAS & SPS
                    SSPL IEMs are maintained in /opt/seagate/<product>/sspl/low-level/iec_log_messages.csv
 ****************************************************************************

 Example IEM generated on official CaStor hardware:
 May 23 21:20:26 castor-dev3-cc1.dco.colo.seagate.com sspl-ll[5589]: IEC: 020006001: File System Statistics: {"Total Space": "7174313371238400", "Free Space": "7170903111577600"}

 Example IEM generated upon an error
 May 23 21:41:34 dhcp-192-168-174-130.stsv.seagate.com sspl-ll[3389]: IEC: 020006002: File System Statistics Error: {"Error_Details": "/bin/sh: hctl: command not found"}

"""
import subprocess
import json


def report_free_space():
    "Report free space as IEM to be sent back to Seagate periodically via RAS & SPS"

    # Gather file system status using 'hctl cluster status'
    command = "hctl cluster status"
    response, error = run_command(command)
    if len(error) > 0:
        # Log an IEM about the error.  IEMS are maintained in sspl/low-level/iec_log_messages.csv
        json_data = {"Error_Details": str(error)}
        command = "sspl-ll-cli --iemloglevel LOG_WARNING --iemlog 'IEC: 020006002: File System Statistics Error: %s'" % \
                    json.dumps(json_data)
        run_command(command)
        print(("Error executing 'hctl cluster status': %s" % str(error)))
        return

    # Parse out Total and Free Space lines in the response
    total_space = "N/A"
    free_space  = "N/A"
    response_rows = response.split("\n")
    for response_row in response_rows:
        if "Total space:" in response_row:
            total_space = response_row.split(":")[1].strip()
        elif "Free space:" in response_row:
            free_space = response_row.split(":")[1].strip()
            break

    # Log values as an IEM using CLI.  RAS will relay back to Seagate's SPS site, https://service-processing-system.seagate.com/
    json_data = {"Total_Space": total_space, "Free_Space": free_space}
    command = "sspl-ll-cli --iemloglevel LOG_INFO --iemlog 'IEC: 020006001: File System Statistics: %s'" % \
                json.dumps(json_data)
    response, error = run_command(command)
    if len(error) > 0:
        # Log an IEM about the error.  IEMs are maintained in sspl/low-level/iec_log_messages.csv
        json_data = {"Error_Details": str(error)}
        command = "sspl-ll-cli --iemloglevel LOG_WARNING --iemlog 'IEC: 020006002: File System Statistics Error: %s'" % \
                    json.dumps(json_data)
        run_command(command)
        print(("Error while logging IEM via CLI: %s" % str(error)))
    else:
        print(("Response: %s" % str(response)))

def run_command(command):
    """Run the command and get the response and error returned"""
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    response, error = process.communicate()
    return response.rstrip('\n'), error.rstrip('\n')


if __name__ == "__main__":
    report_free_space()
