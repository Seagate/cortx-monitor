#!/usr/bin/python3.6

import json
from .manual_test import ManualTest

manTest = ManualTest("PLANECNTRLRMQEGRESSPROCESSOR")

request = "status"
arguments = {'fromdb': None, 'delim': ',\\t', 'cols': 'wGsf', 'json': None, 'ignoreha': False, 'condition': None}
parameters = {'drive_id': None, 'raid_id': None, 'node_id': 'cslco1800', 'debug_id': None}

#request = "job_status"
#arguments = {'uuid':'tester'}
#parameters = {}

file = "/opt/seagate/eos/sspl/low-level/tests/manual/actuator_msgs/plane_cntrl_request.json"
jsonMsg = json.loads(open(file).read())
jsonMsg["message"]["actuator_request_type"]["plane_controller"]["command"] = "%s" % request
jsonMsg["message"]["actuator_request_type"]["plane_controller"]["parameters"] = parameters
jsonMsg["message"]["actuator_request_type"]["plane_controller"]["arguments"] = arguments

#Update the authentication fields in json msg
manTest.addAuthFields(jsonMsg)

# Validate the msg against the schemas
manTest.validate(jsonMsg)

# Encode and publish
message = json.dumps(jsonMsg, ensure_ascii=True).encode('utf8')
manTest.basicPublish(message=message, indent=True, force_wait=True)
