#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
 ****************************************************************************
 Filename:          sspl_free_space.py
 Description:       Report free space as IEM to be sent back to Seagate periodically via RAS & SPS
                    SSPL IEMs are maintained in /opt/seagate/sspl/low-level/iec_log_messages.csv
 Creation Date:     05/23/2017
 Author:            Jake Abernathy

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2017/05/23 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
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
        print "Error executing 'hctl cluster status': %s" % str(error)
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
        print "Error while logging IEM via CLI: %s" % str(error)
    else:
        print "Response: %s" % str(response)

def run_command(command):
    """Run the command and get the response and error returned"""
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    response, error = process.communicate()
    return response.rstrip('\n'), error.rstrip('\n')


if __name__ == "__main__":
    report_free_space()