""" Some utility functions that are shared by both the unit and acceptance
tests.
"""

import json


def generate_service_request_msg(service_name, command):
    """ Generate a service request response message.

    Normally, this would be done by halon.  This function is used to mock
    halon's response message to a service request.
    """
    return json.dumps(json.loads("""
        {{
            "serviceRequest":
            {{
                "serviceName": "{service_name}",
                "command": "{command}"
            }}
        }}
        """.format(service_name=service_name, command=command)))
