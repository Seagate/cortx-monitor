"""
 ****************************************************************************
 Filename:          spiel.py 
 Description:       Handles messages for Spiel requests
                    (Derived from m0spiel tool except for the crap parts...)
 Creation Date:     05/02/2016
 Author:            Jake Abernathy

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

import subprocess

from zope.interface import implements
from actuators.Ispiel import ISpiel

from framework.base.debug import Debug
from framework.utils.service_logging import logger

from actuators.impl.c_api.spielwrapper import Fid, NetXprt, ReqhInitArgs, FsStats, SpielWrapper


class Spiel(Debug):
    """Handles request messages for Spiel"""

    implements(ISpiel)

    ACTUATOR_NAME = "Spiel"

    # Section and keys in configuration file
    SPIEL           = ACTUATOR_NAME.upper()
    LIBMERO_PATH    = 'libmero_path'
    HA_EP           = 'ha_ep'
    CLIENT_EP       = 'client_ep'

    @staticmethod
    def name():
        """ @return: name of the module."""
        return Spiel.ACTUATOR_NAME

    def __init__(self, conf_reader):
        super(Spiel, self).__init__()

        # Read in the configuration values to be used
        self._conf_reader = conf_reader
        self._read_config()

        # Hard-coded for now until the API is completed to retrieve at run-time
        self._spiel_rms_fid = Fid(0x7300000000000004, 100)
        self._rhia_fid      = Fid(0x7200000000000001, 5)
        self._profile_fid   = "0x7000000000000001:0x1"

        self._spiel = None

    def perform_request(self, jsonMsg):
        """Performs the Mero request

        @return: The response string from performing the request
        """
        self._check_debug(jsonMsg)

        response = "N/A"
        try:
            # Parse out the node request to perform
            node_request = jsonMsg.get("actuator_request_type").get("node_controller").get("node_request")
            self._log_debug("perform_request, node_request: %s" % node_request)

            # Parse out the arguments for the RAID action
            spiel_request = node_request[6:].strip()
            self._log_debug("perform_request, spiel request: %s" % spiel_request)

            # Initialize the spiel interface
            #self._init_spiel()

            # Handle different spiel requests
            if "fsstats" in spiel_request:
                self._fs_fid_key = node_request[14:].strip()
                self._log_debug("fs Fid Key: %s" % self._fs_fid_key)
                response = self._get_mero_fs_stats()

        except Exception as e:
            logger.exception(e)
            response = str(e)

        finally:
            # Clean up spiel interface
            if self._spiel:
                self._spiel.spiel_fini()

        return response

    def _init_spiel(self):
        """Initialize Spiel for interacting with Mero"""
        try:
            self._spiel = SpielWrapper(self._mero_lib_path)

            self._spiel.spiel_init(self._ha_ep, self._client_ep)
            self._spiel.cmd_profile_set(self._profile_fid)

        except Exception as e:
            logger.exception(e)

    def _get_mero_fs_stats(self):
        """Retrieve mero fs stats using m0_fs_stats"""
        results = "N/A"
        try:
            # Build the command args to pass to m0_fs_stats
            command = "sudo /opt/seagate/sspl/low-level/libs/m0_fs_stats"
            #command = "sudo /mnt/hgfs/SharedVMfolder/sspl/low-level/libs/m0_fs_stats"
            cmd_args = "{} {} {} {} {}".format(command, self._mero_lib_path, self._ha_ep, 
                                            self._client_ep, self._fs_fid_key)

            p = subprocess.Popen(cmd_args, shell=True,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            output, error = p.communicate()

            logger.info("output: %s" % output)
            logger.info("error: %s" % error)
            if error:
                results = "Error:{}".format(error)
            else:
                results = output

        except OSError as ae:
            logger.exception(ae)
        return output

    def _read_config(self):
        """Read in configuration values"""
        try:
            self._mero_lib_path = self._conf_reader._get_value_with_default(self.SPIEL,
                                                                   self.LIBMERO_PATH,
                                                                   '/usr/lib64/libmero-0.1.0.so')
            self._ha_ep = self._conf_reader._get_value_with_default(self.SPIEL,
                                                                   self.HA_EP,
                                                                   '12345:34:101')
            self._client_ep = self._conf_reader._get_value_with_default(self.SPIEL,
                                                                   self.CLIENT_EP,
                                                                   '12345:34:200')

            logger.info("Mero Spiel config: \nMero lib path: %s \nHA end point: %s \nClient end point: %s" % 
                            (self._mero_lib_path, self._ha_ep, self._client_ep))
        except Exception as e:
            logger.exception(e)