"""
 ****************************************************************************
 Filename:          seddisppatch.py
 Description:       Displatch module for communications with SED libs
 Creation Date:     2/10/2016

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""
from framework.utils.service_logging import logger
from sedutil.sedutil import MachineInfo
import sedutil.sedOps as sedOps

# cFileIO import failed so switched to cStringIO, check with John, what package provides or can leave at cStringIO?
from cStringIO import StringIO


class SedOpDispatch(object):
    machineInfo = None
    subcommand2op = {
      'status': sedOps.Status,
      'configure': sedOps.Configure,
      'disable': sedOps.Disable,
      'erase': sedOps.Erase,
      'rotate': sedOps.Rotate
    }
    @classmethod
    def _initClass(cls):
        cls.machineInfo = MachineInfo()
        cls.keyStore    = cls.machineInfo.getKeyDatabase()
        cls.hostname    = cls.machineInfo.gethostname()
        cls.primary     = cls.machineInfo.primary
        cls.clientType  = cls.machineInfo.clientType()
        cls.processUnknown = cls.machineInfo.haveBaton

    def __init__(self, command, parameters, arguments):
        """
        command     - 'status', 'configure', 'disable', 'erase', 'rotate'
        parameters  -  dictionary with indices 'drive_id', 'raid_id', 'node_id'
        arguments   - command specific parameters
        """
        self._errors = StringIO()
        self._output = ""
        self._status = 0

        if self.machineInfo is None:
            self._initClass()
        try:
            self.operation = self.subcommand2op[command]
        except KeyError:
            self._errors.write("Invalid subcommand")
            self._status = 1
            return

        self.server  = parameters.get('node_id', None)
        self.raidset = parameters.get('raid_id', None)
        self.drive   = parameters.get('drive_id', None)

        if (self.machineInfo.hostname not in self.server and
            self.machineInfo.partner not in self.server):
            self._status = 2
            return

        logger.info("SedOpDispatch, init, server: %s, raidset: %s, drive: %s" % \
                    (self.server, self.raidset, self.drive))
        subparse = getattr(self, 'parse_' + command, None)
        if subparse is not None:
            subparse(arguments)
        self.groups = self.machineInfo.createGroups(self)

    def run(self):
        if not hasattr(self, 'operation'):
            return self._status
        self._status = sedOps.processSedOp(self)
        return self._status

    def parse_status(self, args):
        logger.info("SedOpDispatch, parse_status, args: %s" % args)
        self.yaml       = StringIO()
        self.json       = args.get("json", None)
        self.cols       = args.get("cols", None)
        self.delim      = args.get("delim", None)
        self.condition  = args.get("condition", None)
        self.fromdb     = args.get("fromdb", None)
        self.ignoreha   = args.get("ignoreha", None)

    def parse_erase(self, args):
        logger.info("SedOpDispatch, parse_erase, args: %s" % args)
        self.recovery = args.get("recovery", None)

    @property
    def hostname(self):
        'Provides hostname of machine'
        return self.hostname

    @property
    def status(self):
        'Provides status code of operation: 0: success, 1 or 2: failure'
        return self._status

    @property
    def output(self):
        'Provides string containing status output'
        if hasattr(self, 'yaml'):
            return self.yaml.getvalue()
        return ''

    @property
    def errors(self):
        'Provides string containing error messages'
        return self._errors.getvalue()


