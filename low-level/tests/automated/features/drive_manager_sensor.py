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
    found = False
    for proc in psutil.process_iter():  
        if proc.name == "sspl_ll_d" and \
           proc.status in (psutil.STATUS_RUNNING, psutil.STATUS_SLEEPING):
            found = True
    assert found == True

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

@step(u'When I set all the drives to "([^"]*)"')
def when_i_set_all_the_drives_to_condition(step, condition):
    drives = world.diskmonitor_file.get("drives")
    for drive in drives:
        drive["status"] = condition
    write_drive_manager()
    # Wait for Inotify to trigger
    time.sleep(10)

@step(u'Then SSPL_LL transmits JSON msgs with status "([^"]*)" for all drives and enc "([^"]*)" for a total of "([^"]*)"')
def then_sspl_ll_transmits_json_msgs_with_status_condition_for_all_drives_and_enc_for_a_total_of_total(step, condition, enc, total):
    total_drives = 0
    ingressMsg = world.sspl_modules[RabbitMQingressProcessorTests.name()]._read_my_msgQ()
    sensor_response_type = ingressMsg.get("sensor_response_type").get("disk_status_drivemanager")
    assert sensor_response_type is not None
    encl_sn = ingressMsg.get("sensor_response_type").get("disk_status_drivemanager").get("enclosureSN")
    assert encl_sn == enc
    disk_num = ingressMsg.get("sensor_response_type").get("disk_status_drivemanager").get("diskNum")
    assert disk_num is not None
    disk_status = ingressMsg.get("sensor_response_type").get("disk_status_drivemanager").get("diskStatus")
    assert disk_status == condition
    total_drives += 1

    # Loop thru all messages in queue until and transmit
    while not world.sspl_modules[RabbitMQingressProcessorTests.name()]._is_my_msgQ_empty():
        ingressMsg = world.sspl_modules[RabbitMQingressProcessorTests.name()]._read_my_msgQ()
        sensor_response_type = ingressMsg.get("sensor_response_type").get("disk_status_drivemanager")
        assert sensor_response_type is not None
        encl_sn = ingressMsg.get("sensor_response_type").get("disk_status_drivemanager").get("enclosureSN")
        assert encl_sn == enc
        disk_num = ingressMsg.get("sensor_response_type").get("disk_status_drivemanager").get("diskNum")
        assert disk_num is not None
        disk_status = ingressMsg.get("sensor_response_type").get("disk_status_drivemanager").get("diskStatus")
        assert disk_status == condition
        total_drives += 1

    assert total_drives == int(total)


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
        time.sleep(10)

    # Clear the message queue buffer out
    while not world.sspl_modules[RabbitMQingressProcessorTests.name()]._is_my_msgQ_empty():
        world.sspl_modules[RabbitMQingressProcessorTests.name()]._read_my_msgQ()

def write_drive_manager():
    """Helper function to update the drive_manager.json file"""
    filename="/var/run/diskmonitor/drive_manager.json"
    with open(filename, 'w') as f:
        json.dump(world.diskmonitor_file, f)
