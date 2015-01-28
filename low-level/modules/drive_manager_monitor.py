"""
 ****************************************************************************
 Filename:          drive_manager_monitor.py
 Description:       Monitors the specified file system for changes,
                    creates json messages and notifies rabbitmq thread
                    to broadcast to rabbitmq topic defined in conf file
 Creation Date:     01/14/2015
 Author:            Jake Abernathy

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.

 ****************************************************************************
 All relevant license information (GPL, FreeBSD, etc)
 ****************************************************************************
"""

import Queue
import pyinotify
#from jsonschema import Draft4Validator

from base.monitor_thread import ScheduledMonitorThread 
from utils.service_logging import logger


class DriveManagerMonitor(ScheduledMonitorThread):
     
    MODULE_NAME       = "DriveManagerMonitor"
    PRIORITY          = 2

    # Section and keys in configuration file
    DRIVEMANAGERMONITOR = MODULE_NAME.upper()
    DRIVE_MANAGER_DIR   = 'drivemanager_dir'
    DRIVE_MANAGER_PID   = 'drivemanager_pid'
    

    @staticmethod
    def name():
        """ @return name of the monitoring module. """
        return DriveManagerMonitor.MODULE_NAME

    def __init__(self):
        super(DriveManagerMonitor, self).__init__(self.MODULE_NAME,
                                                  self.PRIORITY)
        self._sentJSONmsg = None    
    
    def initialize(self, rabbitMsgQ, conf_reader):
        """initialize method contains conf_reader if needed"""
        super(DriveManagerMonitor, self).initialize(rabbitMsgQ,
                                                    conf_reader)           
        self._drive_mngr_base_dir  = self._getDrive_Mngr_Dir()
        self._drive_mngr_pid       = self._getDrive_Mngr_Pid()
                
    def shutdown(self):
        """Clean up scheduler queue and gracefully shutdown thread"""
        super(DriveManagerMonitor, self).shutdown() 
        try:            
            logger.info("DriveManagerMonitor, shutdown: removing pid:%s" % self._drive_mngr_pid)        
            os.remove(self._drive_mngr_pid)
        except Exception as ex:
            logger.exception("DriveManagerMonitor, shutdown: %s" % ex)
             
    def run(self):
        """Run the monitoring periodically on its own thread."""
        super(DriveManagerMonitor, self).run()   
        logger.info("Starting thread for '%s'", self.name())                         
        logger.info("DriveManagerMonitor, run, directory: %s" % self._drive_mngr_base_dir)
        
        try:
            # Followed tutorial for pyinotify: https://github.com/seb-m/pyinotify/wiki/Tutorial            
            wm      = pyinotify.WatchManager() 
            
            # Mask events to watch for on the file system
            mask    = pyinotify.IN_DELETE | pyinotify.IN_CREATE | pyinotify.IN_MODIFY         
            
            # Event handler class called by pyinotify when an events occurs on the file system            
            handler = self.InotifyEventHandlerDef()            
            
            # Create the blocking notifier utilizing Linux built-in inotify functionality
            blocking_notifier = pyinotify.Notifier(wm, handler)         
            
            # main config method: mask is what we want to look for 
            #                     rec=True, recursive thru all sub-directories
            #                     auto_add=True, automatically watch new directories   
            wm.add_watch(self._drive_mngr_base_dir, mask, rec=True, auto_add=True)                        
            
            # Loop forever blocking on this thread, monitoring file system 
            #  and firing events to InotifyEventHandler: process_IN_CREATE(), process_IN_DELETE()            
            blocking_notifier.loop()
            
        except Exception as ex:
            # Log it and restart the whole process when a failure occurs      
            logger.exception("DriveManagerMonitor restarting")
            self._scheduler.enter(10, self._priority, self.run, ())  

        logger.info("Finished thread for '%s'", self._module_name)       
             
    def _getDrive_Mngr_Dir(self):
        """Retrieves the drivemanager path to monitor on the file system"""
        return self._conf_reader._get_value_with_default(self.DRIVEMANAGERMONITOR, 
                                                                 self.DRIVE_MANAGER_DIR,
                                                                 '/tmp/dcs/drivemanager')                
    def _getDrive_Mngr_Pid(self):
        """Retrieves the pid file indicating pyinotify is running or not"""
        return self._conf_reader._get_value_with_default(self.DRIVEMANAGERMONITOR, 
                                                                 self.DRIVE_MANAGER_PID,
                                                                 '/var/run/pyinotify.pid')        
    def _send_json_RabbitMQ(self, pathname):
        """Place the json message into the RabbitMQprocessor queue if valid"""
        # Ignore swap files which can occur during testing and clog up logs
        if ".swp" in pathname:
            return
        
        logger.info("DriveManagerMonitor, _send_json_RabbitMQ: pathname %s" % pathname)  
        
        # Convert pathname to Drive object to handle parsing and json conversion, etc
        drive = Drive(pathname, self._drive_mngr_base_dir)
        
        # Obtain json message containing all relevant data
        valid, jsonMsg = drive.toJson()
        
        # Sometimes iNotify sends the same event twice, catch and ignore
        if jsonMsg == self._sentJSONmsg:
            return
        else:
            self._sentJSONmsg = jsonMsg
    
        # If we have a valid json message then place it into the RabbitMQprocessor queue        
        if valid:            
            self._writeRabbitMQ(jsonMsg)
        else:
            logger.info("DriveManagerMonitor, _send_json_RabbitMQ, valid: %s(ignoring)," \
                        "jsonMsg: %s" % (valid, jsonMsg))
    
    
    def InotifyEventHandlerDef(self):
        """Internal event handling class for Inotify"""
        _parent = self 
        
        class InotifyEventHandler(pyinotify.ProcessEvent):                   
            def process_IN_CREATE(self, event):
                """Inherited Callback method from inotify when a create file event occurs"""                                     
                _parent._send_json_RabbitMQ(event.pathname)  
        
            def process_IN_MODIFY(self, event):
                """Inherited Callback method from inotify when a modify file event occurs"""
                _parent._send_json_RabbitMQ(event.pathname)
        
            def process_IN_DELETE(self, event):
                """Inherited Callback method from inotify when a delete file event occurs"""                   
                _parent._send_json_RabbitMQ(event.pathname)
            
        iNotifyEventHandler = InotifyEventHandler()
        return iNotifyEventHandler


class Drive(object):
    """Object representation of a drive"""

    def __init__(self, path, drive_mngr_base_dir):
        super(Drive, self).__init__()        
        self._path = path
        self._drive_mngr_base_dir = drive_mngr_base_dir
        
    def _parse_path(self):
        """Parse the path of the file, return True if valid file name exists in path"""        
        try:
            # Validate the path for the drive
            if "disk" not in self._path:
                logger.warn("Drive, _parse_path: Drive path does not contain the required keyword 'disk'")
                return
                    
            # Remove base dcs dir and split into list parsing out enclosure and drive num
            data_str = self._path[len(self._drive_mngr_base_dir)+1:]    
            path_values = data_str.split("/")
            
            # See if there is a valid filename at the end: serial_number, slot, status
            # Normal path will be: enclosure/disk/drive number
            if len(path_values) < 4:
                return False
            
            # Parse out values for drive            
            self._enclosure = path_values[0]
            self._drive_num = path_values[2]
            
            # Read in the value of the file at the end of the path
            self._filename  = path_values[3]
            with open (self._path, "r") as datafile:
                data = datafile.read().replace('\n', '')
            self._fileValue = data
            return True
        
        except Exception as ex:
            logger.exception("Drive, _parse_path: %s, ignoring event." % ex)
        return False
        
        
    def toJson(self):
        """Returns the JSON representation of a drive"""
        valid = self._parse_path()
        if not valid:
            return (False, None)
        
        # Fill in json object and return it
        # TODO: Expand on this using json api libs and other data about drive stats
#         jsonMsg = {"Enclosure": self._enclosure,
#                    "DriveNum": self._drive_num,
#                    self._filename: self._fileValue}
                    
        jsonMsg = {"title" : "SSPL-LL Monitor Response",
                   "description" : "Seagate Storage Platform Library - Low Level - Monitor Response",
                   "sspl_ll_host": {
                        "fqdn" : "sspl-ll-test.stsv.seagate.com",
                        "ip_addr" : "192.168.174.128",
                        "schema_version" : "1.0.0",
                        "sspl_version" : "1.0.0",
                        "local_time": "Tue Jan 27 17:50:26 MST 2015",                       
                        },
                   "monitor_msg_type": {
                        "disk_status_drivemanager": {
                            "enclosureSN" : self._enclosure,
                            "diskNum" : self._drive_num,
                            "diskSlot" : 0,
                            "diskSN" : "Hard coded test using filename:content",
                            self._filename: self._fileValue,            
                            }
                        }
                   }
        
#         
#         TODO: Validate against schema to catch json errors
#         
#         schema = {
#             "$schema": "http://json-schema.org/schema#",
#             "type": "object",
#             "properties": {
#                 "Enclosure": {"type": "string"},
#                 "DriveNum": {"type": "string"},
#             },
#             "required": ["email"]
#         }        
#         logger.info("IN toJson and ready to validate with schema: %s" % schema)
#         
#         # Validate the message against the schema
#         Draft4Validator.check_schema(schema)
        
        return (True, jsonMsg)
       
       
       
        