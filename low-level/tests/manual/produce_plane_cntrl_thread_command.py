#!/usr/bin/env python

import json
from manual_test import ManualTest

manTest = ManualTest("PLANECNTRLRMQEGRESSPROCESSOR")

file = "/opt/seagate/sspl/low-level/tests/manual/actuator_msgs/thread_cntrl_restart.json"
jsonMsg = json.loads(open(file).read())
jsonMsg["message"]["actuator_request_type"]["thread_controller"]["module_name"] = "PlaneCntrlMsgHandler"
jsonMsg["message"]["actuator_request_type"]["thread_controller"]["thread_request"] = "restart"
jsonMsg["message"]["actuator_request_type"]["thread_controller"]["parameters"] = {'node_id':'cslco1800'}

#Update the authentication fields in json msg
manTest.addAuthFields(jsonMsg)

# Validate the msg against the schemas
manTest.validate(jsonMsg)

# Encode and publish
message = json.dumps(jsonMsg, ensure_ascii=True).encode('utf8')
manTest.basicPublish(message=message, indent=True, force_wait=True)
