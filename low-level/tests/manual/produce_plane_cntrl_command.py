#!/usr/bin/env python

import json
from manual_test import ManualTest

manTest = ManualTest("PLANECNTRLRMQEGRESSPROCESSOR")

request = "status"
arguments = {u'fromdb': None, u'delim': u',\\t', u'cols': u'wGsf', u'json': None, u'ignoreha': False, u'condition': None}
parameters = {u'drive_id': None, u'raid_id': None, u'node_id': u'cslco1800', u'debug_id': None}

#request = "job_status"
#arguments = {'uuid':'tester'}
#parameters = {}

file = "/opt/seagate/sspl/low-level/tests/manual/actuator_msgs/plane_cntrl_request.json"
jsonMsg = json.loads(open(file).read())
jsonMsg["message"]["actuator_request_type"]["plane_controller"]["command"] = u"%s" % request
jsonMsg["message"]["actuator_request_type"]["plane_controller"]["parameters"] = parameters
jsonMsg["message"]["actuator_request_type"]["plane_controller"]["arguments"] = arguments

#Update the authentication fields in json msg
manTest.addAuthFields(jsonMsg)

# Validate the msg against the schemas
manTest.validate(jsonMsg)

# Encode and publish
message = json.dumps(jsonMsg, ensure_ascii=True).encode('utf8')
manTest.basicPublish(message=message, indent=True, force_wait=True)
