""" Lettuce implementation for the service_request.feature. """
import lettuce
import urllib
import os.path
import json

# Note:  We should use the plex registry to programatically generate this URL
# to protect against changes in how plex surfaces apps/providers/etc.  But
# since this is test code, we won't worry about it.
SERVICE_URI = "http://localhost:8080/apps/sspl_hl/providers/service/data"


@lettuce.step(u'When I request "([^"]*)" service "([^"]*)" for all nodes')
def service_cmd_for_all_nodes(_, service, cmd):
    """ Request given service take given action by hitting data provider url.
    """
    url = SERVICE_URI + "?serviceName={service}&command={cmd}".format(
        service=service, cmd=cmd
        )
    urllib.urlopen(url=url)


@lettuce.step(u'Then a serviceRequest message to "([^"]*)" "([^"]*)" is sent')
def servicerequest_msg_sent(_, command, service_name):
    """ Ensure proper message generated and enqueued. """
    # wait for a message to appear in the fake_halond output directory
    lettuce.world.wait_for_condition(
        status_func=lambda: len(os.listdir('/tmp/fake_halond')) > 0,
        max_wait=5,
        timeout_message="Timeout expired while waiting for message to arrive "
        "in fake_halond output directory."
        )

    first_file = sorted(
        os.listdir('/tmp/fake_halond'),
        key=lambda f: os.stat(os.path.join('/tmp/fake_halond', f)).st_mtime
        )[0]
    contents = open(os.path.join('/tmp/fake_halond', first_file), 'r').read()

    expected = json.dumps(json.loads("""
        {{
            "serviceRequest":
            {{
                "serviceName": "{service_name}",
                "command": "{command}"
            }}
        }}
        """.format(service_name=service_name, command=command)))

    assert contents == json.dumps(json.loads(expected)), \
        "Message doesn't match.  Expected '{expected}' but got '{actual}'" \
        .format(expected=expected, actual=contents)

    os.unlink(os.path.join('/tmp/fake_halond', first_file))
