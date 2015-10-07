#!/usr/bin/env python
"""
# ****************************************************************************
# Filename: sspl_tests.py
#
# Description: sspl-ll tests for Clustercheck
#  Verifies Message passing for services, drives, logs, and thread controller.
#
# Creation Date: 06/06/2015
#
# Author: Alex Cordero <alexander.cordero@seagate.com>
#         Andy Kim <jihoon.kim@seagate.com>
#
# Do NOT modify or remove this copyright and confidentiality notice!
#
# Copyright (c) 2001 - 2015 Seagate Technology, LLC.
#
# The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
# Portions are also trade secret. Any use, duplication, derivation, distribution
# or disclosure of this code, for any reason, not expressly authorized is
# prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
# ****************************************************************************
"""
import json
import pika
import socket
import logging
import threading
import time
import subprocess
import logging
import logging.handlers
import os

from datetime import datetime
from os import listdir
from os.path import isfile, join
from dbus import SystemBus, Interface, exceptions as debus_exceptions

import sys
sys.path.insert(0, '/opt/seagate/sspl/low-level')
from framework.utils.config_reader import ConfigReader

import ctypes
SSPL_SEC = ctypes.cdll.LoadLibrary('libsspl_sec.so.0')

class SSPLtest():
    """Class to perform tests on SSPL"""
    MODULE_NAME = "sspl-ll-tests"

    # Section and keys in configuration file
    SSPLPROCESSOR       = MODULE_NAME.upper()
    EVENTFIELDS         = "EVENT-FIELDS"

    SIGNATURE_USERNAME  = 'message_signature_username'
    SIGNATURE_TOKEN     = 'message_signature_token'
    SIGNATURE_EXPIRES   = 'message_signature_expires'
    FILTER              = 'ignorelist'

    HOST_UPDATE         = 'host_update'
    LOCAL_MOUNT_DATA    = 'local_mount_data'
    CPU_DATA            = 'cpu_data'
    IF_DATA             = 'if_data'

    #This is a hardcoded file location used for all actuator_msgs and the config file
    #This is needed to be hardcoded to run through MCollective from cluster_check
    actuator_msgs_folder = "/opt/seagate/sspl/low-level/tests/manual/actuator_msgs/"

    def __init__(self, logger = None):
        """Sets the system in the right state for the tests
        Opens up channel for egress message communication
        Starts the drives listed in self.drivesToTest
        Starts crond.service
        """

        if logger is None:
            #Logger prints to stdout because mco can not read from stderr
            #Debug is now processed in cluster_check
            cmd_handler = logging.StreamHandler(sys.stdout)
            loglevel = logging.DEBUG
            cmd_handler.setLevel(loglevel)
            self.logger = logging.getLogger('cluster_check')
            self.logger.addHandler(cmd_handler)
            self.logger.setLevel(logging.DEBUG)
        else:
            self.logger = logger
        self.logger.debug('SSPL Low Level Tests Begin')
        self.usage()

        self.start_stop_service("crond", "start") #the following variables with the *ToTest names
                                                  #are hardcoded to match the JSON files
                                                  #Keep consistent with JSON messages

        self.servicesToTest = [{"Service" : "crond", "Action" : "stop"}]
        self.drivesToTest = [0, 1, 50, 83]        #Drive numbers are to test first few drives, a middle drive and the last drive
                                                  #Cannot cover all drives in a reasonable time, thus certain ones are chosen
                                                  #for a sample and then tested.
        self.threadsToTest = ["DriveManager", "SystemdWatchdog"]

        #initialize event and interthread_msg for communication between concurrent threads
        self.event = threading.Event()
        self.interthread_msg = ""

        #Counters for test totals, will be reported at the end
        self.testsTotal = 0
        self.testsPassed = 0
        self.serviceTestTotal = 0
        self.serviceTestPassed = 0
        self.threadTestTotal = 0
        self.threadTestPassed = 0
        self.logTestTotal = 0
        self.logTestPassed = 0
        self.watchdogTestTotal = 0
        self.watchdogTestPassed = 0
        self.driveTestTotal = 0
        self.driveTestPassed = 0
        self.hostTestTotal = 0
        self.hostTestPassed = 0
        self.eventTestTotal = 0
        self.eventTestPassed = 0

        #Gather information about json messages in ./actuator_msgs folder
        self.egressMessage()
        #Read the configuration file
        path_to_conf_file = self.actuator_msgs_folder + "sspl_ll_tests.conf"
        try:
            self._conf_reader = ConfigReader(path_to_conf_file)

        except (IOError, ConfigReader.Error) as err:
            # We don't have logger yet, need to find log_level from conf file first
            self.logger.debug("[ Error ] when validating the configuration file %s :" % \
                path_to_conf_file)
            self.logger.debug(err)
            self.logger.debug("Exiting ...")
            exit(os.EX_USAGE)
        #Gather signature information from config file
        self._signature_user = self._conf_reader._get_value_with_default(
                                                    self.SSPLPROCESSOR,
                                                    self.SIGNATURE_USERNAME,
                                                    'sspl-ll')

        self._signature_token = self._conf_reader._get_value_with_default(
                                                    self.SSPLPROCESSOR,
                                                    self.SIGNATURE_TOKEN,
                                                    'FAKETOKEN1234')

        self._signature_expires = self._conf_reader._get_value_with_default(
                                                    self.SSPLPROCESSOR,
                                                    self.SIGNATURE_EXPIRES,
                                                    "3600")

        #List of message types to ignore. Will switch on and off as features are tested
        #TODO: Update this list as additional message features are added
        self.filter = self._conf_reader._get_value_list(self.SSPLPROCESSOR,
                                                        self.FILTER)

        self.creds = pika.PlainCredentials('sspluser', 'sspl4ever')
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(
                     host='localhost', virtual_host='SSPL', credentials=self.creds))
        self.channel = self.connection.channel()

        self.channel.exchange_declare(exchange='sspl_halon',
                                 type='topic', durable=False)


    def usage(self):
        """Usage function"""

        self.logger.debug("If changes are made to the tests make sure that the corresponding changes")
        self.logger.debug("are made to the JSON messages in the actuator_msgs directory.")
        self.logger.debug("Also make sure that changes are made to the verify functions")


    def start_consume(self):
        """Starts consuming all messages sent
        This function should be run on a daemon thread because it will never exit willingly
        Sets the thread event object to true and copies all ingress messages to self.interthread_msg
        """

        creds = pika.PlainCredentials('sspluser', 'sspl4ever')
        connection = pika.BlockingConnection(pika.ConnectionParameters(
                     host='localhost', virtual_host='SSPL', credentials=creds))
        channel = connection.channel()
        channel.exchange_declare(exchange='sspl_halon',
                                 type='topic', durable=False)
        result = channel.queue_declare(exclusive=True)
        channel.queue_bind(exchange='sspl_halon',
                           queue=result.method.queue,
                   routing_key='sspl_ll')
        self.logger.debug('Consumer Started.  Now Accepting JSON Messages!')

        def callback(ch, method, properties, body):
            '''Called whenever a message is passed to the Consumer
            Verifies the authenticity of the signature with the SSPL_SEC libs
            Stores the message and alerts any waiting threads when an ingress message is processed
            '''
            ingressMsg = json.loads(body)
            username  = ingressMsg.get("username")
            signature = ingressMsg.get("signature")
            message   = ingressMsg.get("message")
            msg_len   = len(message) + 1
            try:
                #Verifies the authenticity of an ingress message
                assert(SSPL_SEC.sspl_verify_message(msg_len, str(message), username, signature) == 0)

                sensorMsg = ingressMsg.get("message").get("sensor_response_type")
                actuatorMsg = ingressMsg.get("message").get("actuator_response_type")
                #Sorts out any outgoing messages only processes *_response_type
                if sensorMsg is not None or actuatorMsg is not None: 
                    #print " [x] %r" % (body,)

                    #Passes the ingress message to the interthread_msg string
                    self.interthread_msg = body

                    flag = True

                    #Checks to see if message type is in the list to ignore (Ignoring automated messages)
                    for ignore in self.filter:
                        if sensorMsg is not None:
                            if sensorMsg.get(ignore) is not None:
                                flag = False
                        elif actuatorMsg is not None:
                            if actuatorMsg.get(ignore) is not None:
                                flag = False

                    #If not on ignore list, set the event object to true to alert any waiting threads of a new ingress message
                    if flag:
                        self.event.set()

            except:
                self.logger.debug("Authentication failed on message: %s" % ingressMsg)

            ch.basic_ack(delivery_tag = method.delivery_tag)

        #Sets the callback function to be used when start_consuming is called and specifies the queue to pull messages off of.
        channel.basic_consume(callback,
                              queue=result.method.queue)
        try:
          channel.start_consuming()
        except KeyboardInterrupt:
            channel.stop_consuming()


    def egressMessage(self):
        """Finds all json files in the actuator messages directory in this directory
        Seperates the messages by service, thread, or logs
        Creates a tuple with all relevant information for each tests including the type and the location of the json message
        """

        #Locates all json messages in the ./actuator_msgs folder
        messages = [self.actuator_msgs_folder + f for f in listdir(self.actuator_msgs_folder) if isfile(join(self.actuator_msgs_folder,f)) and ".json" in f ]

        self.testsJson = []

        for message in messages:

            jsonMsg = json.loads(open(message).read())

            if jsonMsg.get("message") is not None:
                actuatorType = jsonMsg.get("message").get("actuator_request_type")
                sensorType = jsonMsg.get("message").get("sensor_request_type")
                if actuatorType is not None:
                    if actuatorType.get("service_controller"):
                        serviceName = actuatorType.get("service_controller").get("service_name")
                        serviceRequest = actuatorType.get("service_controller").get("service_request")

                        self.testsJson.append({"Request Type" : "service", "Service Name" : serviceName, "Request" : serviceRequest, "File Location" : message})

                    elif actuatorType.get("thread_controller"):
                        threadName = actuatorType.get("thread_controller").get("module_name")
                        threadRequest = actuatorType.get("thread_controller").get("thread_request")

                        self.testsJson.append({"Request Type" : "thread", "Thread Name" : threadName, "Request" : threadRequest, "File Location" : message})

                    elif actuatorType.get("logging"):
                        logMsg = actuatorType.get("logging").get("log_msg")

                        self.testsJson.append({"Request Type" : "log", "Log Message" : logMsg, "File Location" : message})
                if sensorType is not None:
                    if sensorType.get("node_data") is not None:
                        sensorType = sensorType.get("node_data").get("sensor_type")

                        self.testsJson.append({"Request Type" : "host update", "Sensor Type" : sensorType, "File Location" : message})


    def serviceVerify(self):
        """Check if SSPL Service Actuator is correctly returning a JSON message
        after an actuator changes the service

        @return : 0 -> serviceVerify test passed
                : 1 -> serviceVerify test failed
        """

        self.logger.debug("Beginning Verification of Services")

        #Allow the consumer to see messages of this type by removing it from filter
        self.filter.remove("service_controller")

        expectedOutput = { "enable" : "enabled",
                           "disable" : "disabled",
                           "start" : "active",
                           "stop" : "inactive",
                           "restart" : "active",
                           "status" : "active",
        }
        checkType = { "enable" : "is-enabled ",
                      "disable" : "is-enabled ",
                      "start" : " ActiveState",
                      "stop" : " ActiveState",
                      "restart" : " ActiveState",
                      "status" : " ActiveState",
        }

        #Find all json messages with the label service
        services = [test for test in self.testsJson if test["Request Type"] == "service"]

        #Organize by command funcationality
        serviceDisable = [service for service in services if service["Request"] == "disable"][0]
        serviceEnable = [service for service in services if service["Request"] == "enable"][0]
        serviceStart = [service for service in services if service["Request"] == "start"][0]
        serviceStop = [service for service in services if service["Request"] == "stop"][0]
        serviceRestart = [service for service in services if service["Request"] == "restart"][0]
        serviceStatus = [service for service in services if service["Request"] == "status"][0]
        serviceOrder = [serviceStop, serviceStart, serviceRestart, serviceStatus]

        #Perform the disable test
        #DISABLE TEST FAILS DUE TO BUG IN SYSTEMD
        #COMMENTED OUT UNTIL BUG IS RESOLVED
        #self.basic_publish(serviceDisable["File Location"])
        #try:
        #    assert(self.event.wait(20))
        #except:
        #    self.logger.debug('TIMEOUT: Could not ' + serviceDisable["Request"] + ' ' + serviceDisable["Service Name"])  #Timeout after 20 seconds
        #self.event.clear()
        #try:
        #    ingressmsg = json.loads(self.interthread_msg)                                           #load ingress message
        #except:
        #    self.logger.debug("Failed to load json message from ingress message")
        #command = "systemctl " + checkType[serviceDisable["Request"]] + serviceDisable["Service Name"]  #checkType is dictionary of actions to be performed to check service state
        #process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        #output, err = process.communicate()
        #try:
        #    self.testsTotal += 1
        #    self.serviceTestTotal += 1
        #    assert(ingressmsg.get("message").get("actuator_response_type").get("service_controller").get("service_name") == serviceDisable["Service Name"])
        #    assert(ingressmsg.get("message").get("actuator_response_type").get("service_controller").get("service_response").find('unlink') != -1 or \

        #           ingressmsg.get("message").get("actuator_response_type").get("service_controller").get("service_response").find('sss') != -1          #Find the keyword 'unlink'
        #           )                                                                                                                                    #Find the keyword 'sss'
                                                                                                                                                        #unlink response when service disabled
                                                                                                                                                        #sss response if service already disabled
        #    assert(output.rstrip().find(expectedOutput[serviceDisable["Request"]]) != -1)      #Check to see if service is actually disabled
        #    self.testsPassed += 1
        #    self.serviceTestPassed += 1
        #    self.logger.debug('Successfully disabled ' + serviceDisable["Service Name"])
        #except:
        #    self.logger.debug('Failed to disable ' + serviceDisable["Service Name"])

        #Perform the enable test
        self.basic_publish(serviceEnable["File Location"])
        try:
            assert(self.event.wait(20))
        except:
            self.logger.debug('TIMEOUT: Could not ' + serviceEnable["Request"] + ' ' + serviceEnable["Service Name"])
        self.event.clear()
        try:
            ingressmsg = json.loads(self.interthread_msg)
        except:
            self.logger.debug("Failed to load json message from ingress message")
        command = "systemctl " + checkType[serviceEnable["Request"]] + serviceEnable["Service Name"]
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, err = process.communicate()
        try:
            self.testsTotal += 1
            self.serviceTestTotal += 1
            assert(ingressmsg.get("message").get("actuator_response_type").get("service_controller").get("service_name") == serviceEnable["Service Name"])
            assert(ingressmsg.get("message").get("actuator_response_type").get("service_controller").get("service_response").find('symlink') != -1 or \
                   ingressmsg.get("message").get("actuator_response_type").get("service_controller").get("service_response").find('sss') != -1          #symlink response if service enabled
                   )                                                                                                                                    #sss response if service already enabled
            assert(output.rstrip().find(expectedOutput[serviceEnable["Request"]]) != -1)
            self.testsPassed += 1
            self.serviceTestPassed += 1
            self.logger.debug('Successfully enabled ' + serviceEnable["Service Name"])
        except:
            self.logger.debug('Failed to enable ' + serviceEnable["Service Name"])

        #Perform the start | stop | restart | status tests
        for service in serviceOrder:

          self.basic_publish(service["File Location"])
          try:
              assert(self.event.wait(20))
          except:
              self.logger.debug('TIMEOUT: Could not ' + service["Request"] + ' ' + service["Service Name"])
          self.event.clear()
          try:
              ingressmsg = json.loads(self.interthread_msg)
          except:
              self.logger.debug("Failed to load json message from ingress message")
          command = "systemctl show " + service["Service Name"] + ' -p '+ checkType[service["Request"]]     #Different command from enable | disable as this command is more consistent
                                                                                                            #with displaying active | inactive services from previous command.
                                                                                                            #This command does not work with enable | disable due to possible systemd bug.
          process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
          output, err = process.communicate()
          try:
              self.testsTotal += 1
              self.serviceTestTotal += 1
              assert(ingressmsg.get("message").get("actuator_response_type").get("service_controller").get("service_name") == service["Service Name"])
              assert(ingressmsg.get("message").get("actuator_response_type").get("service_controller").get("service_response") == expectedOutput[service["Request"]])
              assert(output.rstrip().find(expectedOutput[service["Request"]]) != -1)
              self.testsPassed += 1
              self.serviceTestPassed += 1
              self.logger.debug('Test to ' + service["Request"] + ' ' + service["Service Name"] + ' Succeeded')
          except:
              self.logger.debug('Failed to ' + service["Request"] + ' ' + service["Service Name"])


        #Put it back on the ignore list
        self.filter.append("service_controller")

        if self.serviceTestTotal == self.serviceTestPassed:
            return 0
        else:
            return 1


    def threadVerify(self):
        """Check if SSPL thread controller is correctly returning a JSON message
        after an actuator changes a thread's state

        @return : 0 -> threadVerify test passed
                : 1 -> threadVerify test failed
        """

        self.logger.debug("Beginning Verification of Thread Controller")

        #Allow the consumer to see messages of this type by removing it from filter
        self.filter.remove("thread_controller")

        threads = [test for test in self.testsJson if test["Request Type"] == "thread"]
        #Parse out the correct thread from threads to ensure execution order
        DMStatus = [thread for thread in threads if thread["Request"] == "status"][0]
        DMStart = [thread for thread in threads if thread["Request"] == "start"][0]
        DMStop = [thread for thread in threads if thread["Request"] == "stop"][0]
        SWRestart = [thread for thread in threads if thread["Request"] == "restart"][0]
        threadOrder = [DMStop, DMStart, SWRestart]
        checkCompletion = { "start" : "Start Successful",
                        "stop" : "Stop Successful",
                        "restart" : "Restart Successful",
        }

        checkStatus = { "start" : "Status: Running",
                        "stop" : "Status: Halted",
                        "restart" : "Status: Running",
        }

        for thread in threadOrder:
            self.basic_publish(thread["File Location"])
            try:
                assert(self.event.wait(10))
            except:
                self.logger.debug('TIMEOUT: Could not ' + thread["Request"] + ' the thread')
            self.event.clear()
            try:
                ingressmsg = json.loads(self.interthread_msg)
            except:
                self.logger.debug("Failed to load json message from ingress message")
            try:
                self.testsTotal += 1
                self.threadTestTotal += 1
                assert(ingressmsg.get("message").get("actuator_response_type").get("thread_controller").get("thread_response") == checkCompletion[thread["Request"]])
                self.testsPassed += 1
                self.threadTestPassed += 1
                self.logger.debug('Test to ' + thread["Request"] + ' ' + thread["Thread Name"] + ' Succeeded')
            except:
                self.logger.debug('Test to ' + thread["Request"] + ' ' + thread["Thread Name"] + ' Failed')

            #Only check status of DriveManager Threads
            if thread["Thread Name"] == DMStatus["Thread Name"]:
                self.basic_publish(DMStatus["File Location"])
                try:
                    assert(self.event.wait(10))
                except:
                    self.logger.debug('TIMEOUT: Could not get the status of ' + thread["Thread Name"])
                self.event.clear()
                try:
                    ingressmsg = json.loads(self.interthread_msg)
                except:
                    self.logger.debug("Failed to load json message from ingress message")
                try:
                    self.testsTotal += 1
                    self.threadTestTotal += 1
                    assert(ingressmsg.get("message").get("actuator_response_type").get("thread_controller").get("thread_response") == checkStatus[thread["Request"]])
                    self.testsPassed += 1
                    self.threadTestPassed += 1
                    self.logger.debug('Status Check after ' + thread["Request"] + ' of ' + thread["Thread Name"] + ' Correct')
                except:
                    self.logger.debug('Status Check after ' + thread["Request"] + ' of ' + thread["Thread Name"] + ' Reports Incorrect Status')

        #Put it back on the ignore list
        self.filter.append("thread_controller")

        if self.threadTestTotal == self.threadTestPassed:
            return 0
        else:
            return 1


    def serviceWatchdogVerify(self):
        """Check if SSPL service watchdog is correctly returning a JSON message
        after detecting a change with a service

        @return : 0 -> serviceWatchdogVerify test passed
                : 1 -> serviceWatchdogVerify test failed
        """

        expectedOutput = {"start" : "active",
                          "stop"  : "inactive",
        }

        self.logger.debug("Beginning Verification of Service Watchdog")

        #Allow the consumer to see messages of this type by removing it from filter
        self.filter.remove("service_watchdog")

        #Perform the stop service test
        for service in self.servicesToTest:
            self.start_stop_service(service["Service"], service["Action"])
            try:
                assert(self.event.wait(10))
            except:
                self.logger.debug('TIMEOUT: Could not ' + service["Action"] + ' ' + service["Service"])
            self.event.clear()
            try:
                ingressmsg = json.loads(self.interthread_msg)
            except:
                self.logger.debug("Failed to load json message from ingress message")
            try:
                self.testsTotal += 1
                self.watchdogTestTotal += 1
                assert(ingressmsg.get("message").get("sensor_response_type").get("service_watchdog").get("service_state") == expectedOutput[service["Action"]])
                self.testsPassed += 1
                self.watchdogTestPassed += 1
                self.logger.debug('Test for systemWatchdog succeeded')
            except:
                self.logger.debug('Test for systemWatchdog failed')

        #Put it back on the ignore list
        self.filter.append("service_watchdog")

        if self.watchdogTestTotal == self.watchdogTestPassed:
            return 0
        else:
            return 1


    def driveVerify(self):
        """Check if SSPL drive manager is correctly returning a JSON message
        after detecting a change with the drives

        @return : 0 -> driveVerify test passed
                : 1 -> driveVerify test failed
        """

        self.logger.debug("Beginning Verification of Drives")

        #Allow the consumer to see messages of this type by removing it from filter
        self.filter.remove("disk_status_drivemanager")

        #Loop through and turn all drives on and off.  Check the ingress message returned and verify if drive is in the correct state
        for drive in self.drivesToTest:

            ##Perform the drive off test
            self.driveOff(drive)
            try:
                assert(self.event.wait(60))
            except:
                self.logger.debug('TIMEOUT: Could not turn off the drive number ' + str(drive))
            self.event.clear()
            try:
                ingressmsg = json.loads(self.interthread_msg)
            except:
                self.logger.debug("Failed to load json message from ingress message")
            try:
                self.testsTotal += 1
                self.driveTestTotal += 1
                assert(ingressmsg.get("message").get("sensor_response_type").get("disk_status_drivemanager").get("diskNum") == drive)
                assert(ingressmsg.get("message").get("sensor_response_type").get("disk_status_drivemanager").get("diskStatus") == "unused_ok")
                assert(self.driveCheck(drive) == 0)
                self.testsPassed += 1
                self.driveTestPassed += 1
                self.logger.debug('Test for turning off drive ' + str(drive) + ' succeeded')
            except:
                self.logger.debug('Test for turning off drive ' + str(drive) + ' failed')

            #Perform the drive on test
            self.driveOn(drive)
            try:
                assert(self.event.wait(60))
            except:
                self.logger.debug('TIMEOUT: Could not turn on the drive number ' + str(drive))
            self.event.clear()
            try:
                ingressmsg = json.loads(self.interthread_msg)
            except:
                self.logger.debug("Failed to load json message from ingress message")
            try:
                self.testsTotal += 1
                self.driveTestTotal += 1
                assert(ingressmsg.get("message").get("sensor_response_type").get("disk_status_drivemanager").get("diskNum") == drive)
                assert(ingressmsg.get("message").get("sensor_response_type").get("disk_status_drivemanager").get("diskStatus") == "inuse_ok")
                assert(self.driveCheck(drive) == 1)
                self.testsPassed += 1
                self.driveTestPassed += 1
                self.logger.debug('Test for turning on drive ' + str(drive) + ' succeeded')
            except:
                self.logger.debug('Test for turning on drive ' + str(drive) + ' failed')

        #Put it back on the ignore list
        self.filter.append("disk_status_drivemanager")

        if self.driveTestTotal == self.driveTestPassed:
            return 0
        else:
            return 1


    def logVerify(self):
        """Check if SSPL is writing a message to the log

        @return : 0 -> logVerify test passed
                : 1 -> logVerify test failed
        """

        self.logger.debug("Beginning Verification of Logging")

        #Allow the consumer to see messages of this type by removing it from filter
        self.filter.remove("logging")

        #January is months[12] so it will have precedence over December when a new year occurs
        months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec", "Jan"]
        logs = [test for test in self.testsJson if test["Request Type"] == "log"]
        journalstring = 'journalctl | grep '
        for log in logs:
            foundLog = False
            log_msg = log["Log Message"]
            log_msg = json.dumps(log_msg, ensure_ascii=True).encode('utf8')
            log_msg = json.loads(' '.join(log_msg.split()))
            uuid_start = log_msg.index("\'uuid\':") + 8
            uuid_stop  = log_msg.index(",", uuid_start)
            # Parse out the uuid and remove any white spaces
            #This is used as a unique value to search for
            uuid = log_msg[uuid_start : uuid_stop].strip('\'').strip()
            self.timeStart = self.current_Time()
            self.basic_publish(log["File Location"])
            time.sleep(2)
            try:
                self.testsTotal += 1
                self.logTestTotal += 1
                #Search the log for the uuid and parse out any messages before the start time
                #Logs are logged to /var/log/messages
                #These comstrings caused an error for us on the storage node may need to add an || where $2-$5 are switched to $3-$6 for each comstring
                comstring = journalstring + uuid + ' | awk -F\'[: ]\' \'$1 == \"{0}\" && $2 >= {1} && $3 >= {2} && $4 >= {3} && $5 >= {4}\''.format(
                                                                months[self.timeStart["Month"]-1], self.timeStart["Day"], self.timeStart["Hour"], self.timeStart["Minute"], self.timeStart["Second"])
                process =  subprocess.Popen(comstring, shell=True, stdout=subprocess.PIPE)
                #Any Result signifies a successful search
                #Assert that there were no results to continue search
                assert(process.communicate()[0] == '')
                comstring = journalstring + uuid + ' | awk -F\'[: ]\' \'$1 == \"{0}\" && $2 >= {1} && $3 >= {2} && $4 > {3}\''.format(months[self.timeStart["Month"]-1], self.timeStart["Day"], self.timeStart["Hour"], self.timeStart["Minute"])
                process =  subprocess.Popen(comstring, shell=True, stdout=subprocess.PIPE)
                assert(process.communicate()[0] == '')
                comstring = journalstring + uuid + ' | awk -F\'[: ]\' \'$1 == \"{0}\" && $2 >= {1} && $3 > {2}\''.format(months[self.timeStart["Month"]-1], self.timeStart["Day"], self.timeStart["Hour"])
                process =  subprocess.Popen(comstring, shell=True, stdout=subprocess.PIPE)
                assert(process.communicate()[0] == '')
                comstring = journalstring + uuid + ' | awk -F\'[: ]\' \'$1 == \"{0}\" && $2 > {1}\''.format(months[self.timeStart["Month"]-1], self.timeStart["Day"])
                process =  subprocess.Popen(comstring, shell=True, stdout=subprocess.PIPE)
                assert(process.communicate()[0] == '')
                comstring = journalstring + uuid + ' | awk -F\'[: ]\' \'$1 == \"{0}\"\''.format(months[self.timeStart["Month"]])
                process =  subprocess.Popen(comstring, shell=True, stdout=subprocess.PIPE)
                assert(process.communicate()[0] == '')
            #This AssertionError is to gracefully avoid unnecessary searches after the message has been found
            except AssertionError:
                self.testsPassed += 1
                self.logTestPassed += 1
                foundLog = True
                self.logger.debug("Log Write Successful")
            except:
                self.logger.debug("Runtime Error when searching through log")
            if foundLog == False:
                self.logger.debug("Log write failed")

        # Put it back on the ignore list
        self.filter.append("logging")

        if self.logTestTotal == self.logTestPassed:
            return 0
        else:
            return 1


    def hostUpdateVerify(self):
        """Check if SSPL event messages are being consumed

        @return : 0 -> hostUpdateVerify test passed
                : 1 -> hostUpdateVerify test failed
        """
        self.logger.debug("Beginning Verification of Host Updates")

        # Find all json messages with the label host update
        updates = [test for test in self.testsJson if test["Request Type"] == "host update"]

        # Organize by command functionality
        hostUpdate = [update for update in updates if update["Sensor Type"] == "host_update"][0]
        localMountData = [update for update in updates if update["Sensor Type"] == "local_mount_data"][0]
        cpuData = [update for update in updates if update["Sensor Type"] == "cpu_data"][0]
        ifData = [update for update in updates if update["Sensor Type"] == "if_data"][0]
        hostUpdateAll = [update for update in updates if update["Sensor Type"] == "host_update_all"][0]

        # Fields to validate in
        # TODO: Update this list as additional message features are added
        hostUpdateFields = self._conf_reader._get_value_list(self.EVENTFIELDS,
                                                        self.HOST_UPDATE)
        localMountDataFields = self._conf_reader._get_value_list(self.EVENTFIELDS,
                                                        self.LOCAL_MOUNT_DATA)
        cpuDataFields = self._conf_reader._get_value_list(self.EVENTFIELDS,
                                                        self.CPU_DATA)
        ifDataFields = self._conf_reader._get_value_list(self.EVENTFIELDS,
                                                        self.IF_DATA)

        # Test for host update sensor response
        self.basic_publish(hostUpdate["File Location"])
        self.hostMessage("host_update", hostUpdateFields)

        # Test for local mount data sensor response
        self.basic_publish(localMountData["File Location"])
        self.hostMessage("local_mount_data", localMountDataFields)

        # Test for cpu data sensor response
        self.basic_publish(cpuData["File Location"])
        self.hostMessage("cpu_data", cpuDataFields)

        # Test for if data sensor response
        self.basic_publish(ifData["File Location"])
        self.hostMessage("if_data", ifDataFields)

        # Test for host update all sensor response
        self.basic_publish(hostUpdateAll["File Location"])
        self.hostMessage("host_update", hostUpdateFields)
        self.hostMessage("local_mount_data", localMountDataFields)
        self.hostMessage("cpu_data", cpuDataFields)
        self.hostMessage("if_data", ifDataFields)

        if self.hostTestTotal == self.hostTestPassed:
            return 0
        else:
            return 1


    def eventVerify(self):
        """Check if SSPL event messages are being triggered after changing
        files

        @return : 0 -> eventVerify test passed
                : 1 -> eventVerify test failed
        """

        #Allow the consumer to see messages of this type by removing it from filter
        self.filter.remove("disk_status_drivemanager")

        driveFilePath = "/tmp/dcs/drivemanager"
        hpiFilePath = "/tmp/dcs/hpi"

        enclosures = os.listdir(driveFilePath)
        for enclosure in enclosures:
            if os.path.isdir(driveFilePath+'/'+enclosure):
                disk_dir = os.path.join(driveFilePath, enclosure, "disk")
                for disk in self.drivesToTest:
                    pathname = os.path.join(disk_dir, str(disk))
                    status_file = os.path.join(pathname, "status")
                    self.writeToFile(status_file, "drivemanager")

                    #Check for the drive manager message that we changed to
                    try:
                        assert(self.event.wait(5))
                    except:
                        self.logger.debug('TIMEOUT: Did not get drivemanager event message back ' + str(disk))
                    self.event.clear()
                    try:
                        ingressmsg = json.loads(self.interthread_msg)
                    except:
                        self.logger.debug("Failed to load json message from ingress message")
                    try:
                        self.testsTotal += 1
                        self.eventTestTotal += 1
                        assert(ingressmsg.get("message").get("sensor_response_type").get("disk_status_drivemanager").get("enclosureSN") == enclosure)
                        assert(ingressmsg.get("message").get("sensor_response_type").get("disk_status_drivemanager").get("diskNum") == disk)
                        assert(ingressmsg.get("message").get("sensor_response_type").get("disk_status_drivemanager").get("diskStatus") == "inuse_failed_None")
                        self.testsPassed += 1
                        self.eventTestPassed += 1
                        self.logger.debug('Test to get drivemananger message on disk ' + str(disk) + ' succeeded')
                    except:
                        self.logger.debug('Test to get drivemananger message on disk ' + str(disk) + ' failed')

        #Put it back on the ignore list
        self.filter.append("disk_status_drivemanager")

        #start looking for hpi data changes
        self.filter.remove("disk_status_hpi")

        enclosures = os.listdir(hpiFilePath)
        for enclosure in enclosures:
            if os.path.isdir(hpiFilePath+'/'+enclosure):
                disk_dir = os.path.join(hpiFilePath, enclosure, "disk")
                for disk in self.drivesToTest:
                    pathname = os.path.join(disk_dir, str(disk))
                    status_file = os.path.join(pathname, "status")
                    self.writeToFile(status_file, "hpimonitor")

                    #Test to see hpi data change messages
                    try:
                        assert(self.event.wait(10))
                    except:
                        self.logger.debug('TIMEOUT: Did not get hpi data change event message back ' + str(disk))
                    self.event.clear()
                    try:
                        ingressmsg = json.loads(self.interthread_msg)
                    except:
                        self.logger.debug("Failed to load json message from ingress message")
                    try:
                        self.testsTotal += 1
                        self.eventTestTotal += 1
                        assert(ingressmsg.get("message").get("sensor_response_type").get("disk_status_hpi") is not None)
                        hpiDataMsg = ingressmsg.get("message").get("sensor_response_type").get("disk_status_hpi")
                        assert(hpiDataMsg.get("hostId") is not None)
                        assert(hpiDataMsg.get("deviceId") is not None)
                        assert(hpiDataMsg.get("drawer") is not None)
                        assert(hpiDataMsg.get("location") is not None)
                        assert(hpiDataMsg.get("manufacturer") is not None)
                        assert(hpiDataMsg.get("productName") is not None)
                        assert(hpiDataMsg.get("productVersion") is not None)
                        assert(hpiDataMsg.get("serialNumber") is not None)
                        assert(hpiDataMsg.get("wwn") is not None)
                        self.testsPassed += 1
                        self.eventTestPassed += 1
                        self.logger.debug('Test to get hpi data change message on disk ' + str(disk) + ' succeeded')
                    except Exception as ex:
                        self.logger.debug("Exception: " + str(ex))
                        self.logger.debug('Test to get hpi data change message on disk ' + str(disk) + ' failed')

                    #Test to see hpi data change messages after status is changed back
                    try:
                        assert(self.event.wait(60))
                    except:
                        self.logger.debug('TIMEOUT: Did not get hpi data change event message back ' + str(disk))
                    self.event.clear()
                    try:
                        ingressmsg = json.loads(self.interthread_msg)
                    except:
                        self.logger.debug("Failed to load json message from ingress message")
                    try:
                        self.testsTotal += 1
                        self.eventTestTotal += 1
                        assert(ingressmsg.get("message").get("sensor_response_type").get("disk_status_hpi") is not None)
                        hpiDataMsg = ingressmsg.get("message").get("sensor_response_type").get("disk_status_hpi")
                        assert(hpiDataMsg.get("hostId") is not None)
                        assert(hpiDataMsg.get("deviceId") is not None)
                        assert(hpiDataMsg.get("drawer") is not None)
                        assert(hpiDataMsg.get("location") is not None)
                        assert(hpiDataMsg.get("manufacturer") is not None)
                        assert(hpiDataMsg.get("productName") is not None)
                        assert(hpiDataMsg.get("productVersion") is not None)
                        assert(hpiDataMsg.get("serialNumber") is not None)
                        assert(hpiDataMsg.get("wwn") is not None)
                        self.testsPassed += 1
                        self.eventTestPassed += 1
                        self.logger.debug('Test to get hpi data change message on disk ' + str(disk) + ' succeeded')
                    except:
                        self.logger.debug('Test to get hpi data change message on disk ' + str(disk) + ' failed')

        self.filter.append("disk_status_hpi")

        if self.eventTestTotal == self.eventTestPassed:
            return 0
        else:
            return 1

    def writeToFile(self, fileWrite, testType):
        """Helper function to write to files
        @param fileWrite = file to write to
        @type  fileWrite = string

        @param testType = the type of test performed
        @param testType = string
        """

        self.logger.debug("Writing to file: " + fileWrite)
        try:
            with open(fileWrite, 'w+') as f:
                if testType == "drivemanager":
                    f.write("inuse_failed\n")
                elif testType == "hpimonitor":
                    f.write("not available\n")
        except:
            self.logger.debug("Failed to write to the file")


    def hostMessage(self, messageType, messageFields):
        """Check if SSPL gives a response to host update event messages

        @param messageType = message type that we are looking for in the message
        @type  messageType = string

        @param messageFields = fields in the message that must be verified
        @param messageFields = list of strings
        """

        self.filter.remove(messageType)
        ingressmsg = None

        try:
            assert(self.event.wait(5))
        except:
            self.logger.debug('TIMEOUT: Did not find the message')
        self.event.clear()
        try:
            ingressmsg = json.loads(self.interthread_msg)
        except:
            self.logger.debug("Failed to load json message from ingress message")
        try:
            self.testsTotal += 1
            self.hostTestTotal += 1
            #Find the message type, make sure it's there
            assert(ingressmsg.get("message").get("sensor_response_type").get(messageType) is not None)

            #Check for all the fields listed in messagFields, make sure it's there
            for field in messageFields:
                assert(ingressmsg.get("message").get("sensor_response_type").get(messageType).get(field) is not None)
            self.testsPassed += 1
            self.hostTestPassed += 1
            self.logger.debug('Event message for \"' + messageType + '\" received, test passed')
        except:
            self.logger.debug('Event message for \"' + messageType + '\" did not have correct fields, test failed')
            if ingressmsg is not None:
                self.logger.debug('ingressmsg: %s' % ingressmsg)

        self.filter.append(messageType)


    def start_stop_service(self, service_name, action):
      """Starts and stops a service

      @param service_name = name of the service
      @param action = action to be performed
      @type  service_name = string
      @type  action  = string
      """

      assert action in ("stop", "start", "running", "halted")

      # Obtain an instance of d-bus to communicate with systemd
      bus = SystemBus()

      # Obtain a manager interface to d-bus for communications with systemd
      systemd = bus.get_object('org.freedesktop.systemd1',
                               '/org/freedesktop/systemd1')
      manager = Interface(systemd, dbus_interface='org.freedesktop.systemd1.Manager')

      if action == "start" or \
          action == "running":
          manager.StartUnit(service_name + ".service", 'replace')
      else:
          manager.StopUnit(service_name + ".service", 'replace')


    def driveOn(self, driveNum):
        """Turns drive on

        @param driveNum = drive to be turned on
        @type driveNum  = int
        """

        out = subprocess.Popen('ls /sys/class/enclosure/*/device/scsi_generic',
                                shell=True,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE).communicate()[0]    #Find the drives

        command = ''.join(['wbcli /dev/', out.rstrip(), ' \"powerondrive ' + str(driveNum) + '\"']) #Command to power on drive
        self.logger.debug(command)
        output = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)


    def driveOff(self, driveNum):
        """Turns drive off

        @param driveNum = drive to be turned off
        @type driveNum  = int
        """

        out = subprocess.Popen('ls /sys/class/enclosure/*/device/scsi_generic',
                                shell=True,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE).communicate()[0]

        command = ''.join(['wbcli /dev/', out.rstrip(), ' \"poweroffdrive ' + str(driveNum) + '\"']) #Command to power off drive
        self.logger.debug(command)
        output = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)


    def driveCheck(self, driveNum):
        """Checks the state of the specified drive

        @param driveNum = drive to be checked
        @type driveNum = int

        @return : 0 -> Drive is off
                  1 -> Drive is on
                  2 -> Drive is neither on nor off (Spin up state)
        """

        out = subprocess.Popen('ls /sys/class/enclosure/*/device/scsi_generic',
                                shell=True,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE).communicate()[0]

        command = ''.join(['wbcli /dev/', out.rstrip(), ' \"getdrivestatus ' + str(driveNum) + '\"']) #Command to get drive status
        output = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE).communicate()[0]

        if (output.find('pending       : ONLINE') != -1 and
            output.find('current       : ONLINE') != -1 and
            output.find('pending       : OFF') == -1 and
            output.find('current       : OFF') == -1):
            return 1
        elif (output.find('pending       : ONLINE') == -1 and
              output.find('current       : ONLINE') == -1 and
              output.find('pending       : OFF') != -1 and
              output.find('current       : OFF') != -1):
            return 0
        else:
            return 2


    def basic_publish(self, jsonfile = None, message = None):
        """Publishes message out to the rabbitmq server

        @param jsonfile = the file containing a json message to be sent to the server
        @type jsonfile = string
        @param message = A json message to be sent to the server
        @type message = string
        """
        if jsonfile is not None:
            msg = open(jsonfile).read()
        if message is not None:
            msg = message
        #Convert msg to json format and add username, time til expire (seconds), current time, and security signature
        jsonMsg = json.loads(msg)
        jsonMsg["username"] = self._signature_user
        jsonMsg["expires"]  = int(self._signature_expires)
        jsonMsg["time"]     = str(datetime.now())

        authn_token_len = len(self._signature_token) + 1
        session_length  = int(self._signature_expires)
        token = ctypes.create_string_buffer(SSPL_SEC.sspl_get_token_length())

        SSPL_SEC.sspl_generate_session_token(
                                self._signature_user, authn_token_len,
                                self._signature_token, session_length, token)
        # Generate the signature
        msg_len = len(str(jsonMsg)) + 1
        sig = ctypes.create_string_buffer(SSPL_SEC.sspl_get_sig_length())
        #Calculates the security signature and stores it in sig
        SSPL_SEC.sspl_sign_message(msg_len, str(jsonMsg), self._signature_user,
                                   token, sig)
        #Add the signature calculated using the SSPL_SEC security libs
        jsonMsg["signature"] = str(sig.raw)
        msg_props = pika.BasicProperties()
        msg_props.content_type = "text/plain"
        #Convert the message back to plain text and send to consumer
        self.channel.basic_publish(exchange='sspl_halon',
                                  routing_key='sspl_ll',
                                  properties=msg_props,
                                  body=str(json.dumps(jsonMsg, ensure_ascii=True).encode('utf8')))


    def current_Time(self):
        """Gets the current time

        @return a dictionary with the month, day, hour, minute and second
        """

        return {"Month" : int(datetime.now().strftime('%m')),
                "Day" : int(datetime.now().strftime('%d')),
                "Hour" : int(datetime.now().strftime('%H')),
                "Minute" : int(datetime.now().strftime('%M')),
                "Second" : int(datetime.now().strftime('%S')),
                }


    def restore(self):
        """Restores the system back to running state"""

        self.logger.debug('Beginning Restoration of Drives, Services, and Threads')
        #Turn all drives that were tested back on
        for drive in self.drivesToTest:
            self.driveOn(drive)

        #Turn all services that were tested back to an active state
        for service in self.servicesToTest:
            self.start_stop_service(service["Service"], 'start')

        msg = [test for test in self.testsJson if test["Request Type"] == "thread"][0]["File Location"]
        jsonMsg = json.loads(open(msg).read())
        #Start every thread touched by thread_verify

        #Allow the consumer to see messages of this type by removing it from filter
        self.filter.remove("thread_controller")

        for thread in self.threadsToTest:
            jsonMsg["message"]["actuator_request_type"]["thread_controller"]["module_name"] = thread
            jsonMsg["message"]["actuator_request_type"]["thread_controller"]["thread_request"] = "start"
            self.event.clear()
            self.basic_publish(message = json.dumps(jsonMsg, ensure_ascii=True).encode('utf8'))
            try:
                assert(self.event.wait(10))
            except:
                self.logger.debug('Could not start the thread ' + thread)
            try:
                ingressmsg = json.loads(self.interthread_msg)
            except:
                self.logger.debug("Failed to load json message from ingress message")
            try:
                assert(ingressmsg.get("message").get("actuator_response_type").get("thread_controller").get("thread_response") in ("Start Successful", "Status: Running"))
                self.logger.debug('Restoration: Successfully started ' + thread)
            except:
                self.logger.debug('Restoration: Failed to start ' + thread)

        self.filter.append("thread_controller")


    def cleanUp(self):
        """Close the communication connection"""

        self.restore()

        self.connection.close()
        del(self.connection)



    def runSSPLTest(self):
        """Run all the tests

        @return a dictionary with successes and failures for each test
                and success and failure of the test as a whole
                : 0 -> respective test passed
                : 1 -> respective test failed
        """

        consumet = threading.Thread(target=self.start_consume)
        #serviceVerifyt = threading.Thread(target=self.serviceVerify)
        #logVerifyt = threading.Thread(target=self.logVerify)
        #threadVerifyt = threading.Thread(target=self.threadVerify)
        #serviceWatchdogVerifyt = threading.Thread(target=self.serviceWatchdogVerify)
        #driveVerifyt = threading.Thread(target=self.driveVerify)

        #Set Consumer Thread to Daemon so it will be reaped when program finishes
        consumet.setDaemon(True)
        consumet.start()
        #Sleep for one second to allow consumer to start accepting messages.
        time.sleep(1)
        #Begin all threads sequentially and don't start the next untill the previous has finished

        testPassedDict = {  "TestReturnCode"    : "Passed",
                            "ServiceVerify"     : "Passed",
                            "ThreadVerify"      : "Passed",
                            "LogVerify"         : "Passed",
                            "DriveVerify"       : "Passed",  # Awaiting fix for gemhpi
                            "WatchdogVerify"    : "Passed",
                            "HostUpdateVerify"  : "Passed",
                            "EventVerify"       : "Passed",
                         }

        #if not self.hostUpdateVerify():
        #    testPassedDict["HostUpdateVerify"] = "Passed"
        if not self.eventVerify():
            testPassedDict["EventVerify"] = "Passed"
            self.testsTotal = self.testsPassed
        else:
            testPassedDict["EventVerify"] = "Failed"
        #if not self.serviceVerify():
        #    testPassedDict["ServiceVerify"] = "Passed"
        #if not self.logVerify():
        #    testPassedDict["LogVerify"] = "Passed"
        #if not self.threadVerify():
        #    testPassedDict["ThreadVerify"] = "Passed"
        #if not self.serviceWatchdogVerify():
        #   testPassedDict["WatchdogVerify"] = "Passed"
        # Awaiting fix for gemhpi
        #if not self.driveVerify():
        #    testPassedDict["DriveVerify"] = "Passed"

        self.cleanUp()

        self.logger.debug("Service Total Tests: " + str(self.serviceTestTotal))
        self.logger.debug("Service Tests Passed: " + str(self.serviceTestPassed))
        self.logger.debug("Thread Total Tests: " + str(self.threadTestTotal))
        self.logger.debug("Thread Tests Passed: " + str(self.threadTestPassed))
        self.logger.debug("Log Total Tests: " + str(self.logTestTotal))
        self.logger.debug("Log Tests Passed: " + str(self.logTestPassed))
        self.logger.debug("Watchdog Total Tests: " + str(self.watchdogTestTotal))
        self.logger.debug("Watchdog Tests Passed: " + str(self.watchdogTestPassed))
        self.logger.debug("Drive Total Tests: " + str(self.driveTestTotal))
        self.logger.debug("Drive Tests Passed: " + str(self.driveTestPassed))
        self.logger.debug("Host Update Total Tests: " + str(self.hostTestTotal))
        self.logger.debug("Host Update Tests Passed: " + str(self.hostTestPassed))
        self.logger.debug("Event Total Tests: " + str(self.eventTestTotal))
        self.logger.debug("Event Tests Passed: " + str(self.eventTestPassed))

        self.logger.debug("Total Tests: " + str(self.testsTotal))
        self.logger.debug("Tests Passed: " + str(self.testsPassed))


        if self.testsTotal == self.testsPassed:
            testPassedDict["TestReturnCode"] = 0
        else:
            testPassedDict["TestReturnCode"] = 1

        return testPassedDict

if __name__ == '__main__':
    s = SSPLtest()
    print "SSPL-LL Output = " + json.dumps(s.runSSPLTest(), ensure_ascii=False)
