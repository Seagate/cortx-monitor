#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import pika
import socket

creds = pika.PlainCredentials('sspluser', 'sspl4ever')
connection = pika.BlockingConnection(pika.ConnectionParameters(
        host='localhost', virtual_host='SSPL', credentials=creds))
channel = connection.channel()

channel.exchange_declare(exchange='sspl_iem',
                         type='topic', durable=False)

msg_props = pika.BasicProperties()
msg_props.content_type = "text/plain"

jsonMsg = "Sep 25 02:51:56 dvtrack00 plex info: IEC: 001002001: Rules Engine Event changed state from CONFIRMED to RESOLVED: {‘resolved_time': 1411638715.990002, 'state': 'RESOLVED', 'version': 1, 'uuid': '056184f4-43e2-11e4-923d-001e6739c920', 'event_code': '001001001', 'confirmed_time': 1411560775.977796, 'tracking_start_ts': 1411559875.990503, 'id': '001001001:10114:21', 'event_data': {'host_id': u'10114', 'dcs_timestamp': '1411559850', 'disk_status': u'Failed', 'disk_slot': u'21', 'serial_number': u'SHX0965000G02FG'}}"


channel.basic_publish(exchange='sspl_iem',
                      routing_key='sspl_ll',
                      properties=msg_props, 
                      body=str(jsonMsg))          

print "Successfully Sent: %s" % jsonMsg

connection.close()
del(connection)




