#!/usr/bin/python3

# Copyright (c) 2020 Seagate Technology LLC and/or its Affiliates
#
# This program is free software: you can redistribute it and/or modify it under the
# terms of the GNU Affero General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
# PARTICULAR PURPOSE. See the GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License along
# with this program. If not, see <https://www.gnu.org/licenses/>. For any questions
# about this software or licensing, please email opensource@seagate.com or
# cortx-questions@seagate.com.


import json
from .manual_test import ManualTest

manTest = ManualTest("PLANECNTRLRMQEGRESSPROCESSOR")

request = "status"
arguments = {'fromdb': None, 'delim': ',\\t', 'cols': 'wGsf', 'json': None, 'ignoreha': False, 'condition': None}
parameters = {'drive_id': None, 'raid_id': None, 'node_id': 'cslco1800', 'debug_id': None}

#request = "job_status"
#arguments = {'uuid':'tester'}
#parameters = {}

file = "/opt/seagate/cortx/sspl/low-level/tests/manual/actuator_msgs/plane_cntrl_request.json"
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
