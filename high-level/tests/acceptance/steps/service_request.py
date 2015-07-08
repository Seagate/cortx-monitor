""" Lettuce implementation for the service_request.feature. """
import lettuce
import urllib
import os.path
import json
import subprocess
import common

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


@lettuce.step(u'When I run "([^"]*)"')
def when_i_run(_, cli_command):
    """ Run a CLI command.  """
    lettuce.world.exitcode = subprocess.call(cli_command.split())


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

    expected = common.generate_service_request_msg(
        service_name=service_name, command=command
        )

    assert contents == json.dumps(json.loads(expected)), \
        "Message doesn't match.  Expected '{expected}' but got '{actual}'" \
        .format(expected=expected, actual=contents)

    os.unlink(os.path.join('/tmp/fake_halond', first_file))


@lettuce.step(u'the exit code is "([^"]*)"')
def exit_code_is_x(_, exitcode):
    """ Ensure expected exit code for previously run shell command.

    It's expected that 'When I run '<cmd>' has been previously called.
    """
    assert lettuce.world.exitcode == int(exitcode), \
        "Error: exit code mismatch.  Expected {expected} but got {actual}" \
        .format(
            expected=exitcode,
            actual=lettuce.world.exitcode
        )
