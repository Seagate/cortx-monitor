#!/usr/bin/env python
# -*- coding: utf-8 -*-

from manual_test import ManualTest

manTest = ManualTest("LOGGINGPROCESSOR")
jsonMsg = "Sep 25 02:51:56 dvtrack00 plex debug: IEC: 001002001: Rules Engine Event changed state from CONFIRMED to RESOLVED: {‘resolved_time': 1411638715.990002, 'state': 'RESOLVED', 'version': 1, 'uuid': '056184f4-43e2-11e4-923d-001e6739c920', 'event_code': '001001001', 'confirmed_time': 1411560775.977796, 'tracking_start_ts': 1411559875.990503, 'id': '001001001:10114:21', 'event_data': {'host_id': u'10114', 'dcs_timestamp': '1411559850', 'disk_status': u'Failed', 'disk_slot': u'21', 'serial_number': u'SHX0965000G02FG'}}"
manTest.basicPublish(message = jsonMsg, wait_for_response = False)
