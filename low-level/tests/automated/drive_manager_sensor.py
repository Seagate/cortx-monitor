# -*- coding: utf-8 -*-
from lettuce import *

import psutil
import time
import json
import os

# Add the top level directory to the sys.path to access classes
topdir = os.path.dirname(os.path.dirname(os.path.dirname \
            (os.path.dirname(os.path.abspath(__file__)))))
os.sys.path.insert(0, topdir)

from tests.automated.rabbitmq.rabbitmq_ingress_processor_tests import RabbitMQingressProcessorTests
from framework.rabbitmq.rabbitmq_egress_processor import RabbitMQegressProcessor


@step(u'Given that all drives are set to "([^"]*)" and sspl is started')
def given_that_all_drives_are_set_to_condition_and_sspl_is_started(step, condition):
    set_all_drives(condition)

    # Check that the state for sspl_ll service is active
    found = False

    # Support for python-psutil < 2.1.3
    for proc in psutil.process_iter():
        if proc.name == "sspl_ll_d" and \
           proc.status in (psutil.STATUS_RUNNING, psutil.STATUS_SLEEPING):
               found = True

    # Support for python-psutil 2.1.3+
    if found == False:
        for proc in psutil.process_iter():
            pinfo = proc.as_dict(attrs=['name', 'status'])
            if pinfo['name'] == "sspl_ll_d" and \
                pinfo['status'] in (psutil.STATUS_RUNNING, psutil.STATUS_SLEEPING):
                    found = True

    assert found == True

    # Clear the message queue buffer out
    while not world.sspl_modules[RabbitMQingressProcessorTests.name()]._is_my_msgQ_empty():
        world.sspl_modules[RabbitMQingressProcessorTests.name()]._read_my_msgQ()

@step(u'When I set the "([^"]*)" to "([^"]*)" with serial number "([^"]*)"')
def when_i_set_the_drive_pos_to_condition_with_serial_number_serial_number(step, drive_pos, condition, serial_num):
    print("\tdrive_pos: %s" % drive_pos)
    drives = world.diskmonitor_file.get("drives")
    drive = (drive for drive in drives if drive["serial_number"] == serial_num).next()
    drive["status"] = condition
    write_drive_manager()

@step(u'Then SSPL_LL transmits a JSON msg with status inuse_failed for disk number "([^"]*)" and enc "([^"]*)"')
        # changed and SSPL-LL sends a JSON message with status, enclosure
        # num and disk num for first drive
def then_sspl_ll_transmits_a_json_msg_with_status_inuse_failed_for_disk_number_disk_num_and_enc(step, disk_num, enc):
     # TODO: Use an instance of JournalD sensor to monitor logs showing that SSPL-LL performed the correct action
     ingressMsg = world.sspl_modules[RabbitMQingressProcessorTests.name()]._read_my_msgQ()
     sensor_response_type = ingressMsg.get("sensor_response_type").get("disk_status_drivemanager")
     assert sensor_response_type is not None
     encl_sn = ingressMsg.get("sensor_response_type").get("disk_status_drivemanager").get("enclosureSN")
     assert encl_sn == enc
     disk_num = ingressMsg.get("sensor_response_type").get("disk_status_drivemanager").get("diskNum")
     assert disk_num == disk_num
     disk_status = ingressMsg.get("sensor_response_type").get("disk_status_drivemanager").get("diskStatus")
     assert disk_status == "inuse_failed"

@step(u'When I set "([^"]*)" drives to "([^"]*)"')
def when_i_set_total_drives_to_condition(step, total, condition):
    drives = world.diskmonitor_file.get("drives")
    curr = 0;
    for drive in drives:
        drive["status"] = condition
        curr += 1
        if curr == int(total):
            break
    write_drive_manager()

@step(u'Then SSPL_LL transmits JSON msgs with status "([^"]*)" for "([^"]*)" drives for enclosure "([^"]*)"')
def then_sspl_ll_transmits_json_msgs_with_status_condition_for_total_drives_for_enclosure_enc(step, condition, total_drives, enc):    
    total = 0
    while total != int(total_drives):
        ingressMsg = world.sspl_modules[RabbitMQingressProcessorTests.name()]._read_my_msgQ()
        print("ingressMsg: %s" % ingressMsg)
        sensor_response_type = ingressMsg.get("sensor_response_type").get("disk_status_drivemanager")
        assert sensor_response_type is not None
        encl_sn = ingressMsg.get("sensor_response_type").get("disk_status_drivemanager").get("enclosureSN")
        assert encl_sn == enc
        disk_num = ingressMsg.get("sensor_response_type").get("disk_status_drivemanager").get("diskNum")
        assert disk_num is not None
        disk_status = ingressMsg.get("sensor_response_type").get("disk_status_drivemanager").get("diskStatus")
        assert disk_status == condition
        total += 1
        print("total: %s" % total)

    assert total == int(total_drives)

def set_all_drives(condition):
    """Helper function to set all drives to the same condition"""    
    drives = world.diskmonitor_file.get("drives")
    dirty = False
    for drive in drives:
        if drive["status"] != condition:
            drive["status"] = condition
            dirty = True
    write_drive_manager()

    # If changes were made then wait for Inotify to trigger
    if dirty == True:
        time.sleep(15)

    # Clear the message queue buffer out
    while not world.sspl_modules[RabbitMQingressProcessorTests.name()]._is_my_msgQ_empty():
        world.sspl_modules[RabbitMQingressProcessorTests.name()]._read_my_msgQ()

def write_drive_manager():
    """Helper function to update the drive_manager.json file"""
    filename="/var/run/diskmonitor/drive_manager.json"
    with open(filename, 'w') as f:
        json.dump(world.diskmonitor_file, f)
