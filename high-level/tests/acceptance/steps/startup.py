""" Functions that run at startup/shutdown of the lettuce acceptance tests. """
import lettuce
import subprocess
import time
import os.path

RABBITMQCTL = '/usr/sbin/rabbitmqctl'


# pylint gets confused by @lettuce.before.all... not sure why.
# pylint: disable=no-member
@lettuce.before.all
# pylint: enable=no-member
def initial_setup():
    """ Ensures initial state is reasonable.

    Ensures rabbitmq, plex, and fake_halond are started
    Ensures sspl_hl app is installed.
    """
    _ensure_rabbitmq_running()
    _ensure_rabbitmq_settings()
    _ensure_plex_running()
    _install_plex_apps()
    _disable_plex_auth()
    _restart_plex()
    _start_fake_halond()
    time.sleep(5)


@lettuce.after.all
def _stop_fake_halond(_):
    lettuce.world.fake_halond_process.terminate()


def _ensure_rabbitmq_running():
    with open('/dev/null', 'w') as devnull:
        status = subprocess.call(
            ['sudo', '/usr/sbin/rabbitmqctl', 'status'],
            stdout=devnull
            )
        if status != 0:
            subprocess.Popen(
                ['sudo', '/usr/sbin/rabbitmq-server'],
                stdout=devnull
                )

            def _is_rabbitmq_running():
                # 'status' by itself seems insufficient.  We'll also wait for
                # list_vhosts to be ready.  ... Update: still seems to be
                # insufficient.  So we'll add a sleep.  :(
                status = subprocess.call(
                    ['sudo', '/usr/sbin/rabbitmqctl', 'status'],
                    stdout=devnull
                    )
                if status != 0:
                    return False

                status = subprocess.call(
                    ['sudo', '/usr/sbin/rabbitmqctl', 'list_vhosts'],
                    stdout=devnull
                    )
                if status != 0:
                    return False

                time.sleep(2)
                return True

            lettuce.world.wait_for_condition(
                status_func=_is_rabbitmq_running,
                max_wait=10,
                timeout_message="Timeout expired while waiting for rabbitmq "
                "to start"
                )


def _recreate_vhost(virtual_host):
    """ Recreates the specified vhost.

    The vhost will be deleted if it already exists and then created.

    @type virtual_host:           string
    @param virtual_host:          The vhost to (re)create.
    """
    vhosts = subprocess.check_output(
        ['sudo', RABBITMQCTL, 'list_vhosts']
        ).split('\n')
    assert vhosts[0] == 'Listing vhosts ...'
    assert vhosts[-2] == '...done.'
    assert vhosts[-1] == ''
    for vhost in vhosts[1:-1]:
        if vhost == virtual_host:
            subprocess.check_call(
                ['sudo', RABBITMQCTL, 'delete_vhost', virtual_host]
                )
            break
    subprocess.check_call(['sudo', RABBITMQCTL, 'add_vhost', virtual_host])


def _recreate_user(username, password, virtual_host):
    """ Recreate the rabbitmq user.

    The user is deleted (if it exists) and then created with .* permissions for
    conf,write,read on the specified virtual_host.

    @type username:               string
    @param username:              The user to recreate.
    @type password:               string
    @param passowrd:              The new password for the specified user.
    @type virtual_host:           string
    @param virtual_host:          The vhost on which the permissions will be
                                  set.
    """
    users = subprocess.check_output(
        ['sudo', RABBITMQCTL, 'list_users']
        ).split('\n')
    assert users[0] == 'Listing users ...'
    assert users[-2] == '...done.'
    assert users[-1] == ''
    for userspec in users[1:-1]:
        user = userspec.split()[0]
        if user == username:
            subprocess.check_call(
                ['sudo', RABBITMQCTL, 'delete_user', username]
                )
            break
    subprocess.check_call(
        ['sudo', RABBITMQCTL, 'add_user', username, password]
        )
    subprocess.check_call(
        [
            'sudo', RABBITMQCTL, 'set_permissions',
            '-p', virtual_host,
            username, '.*', '.*', '.*'
        ])
    subprocess.check_call(
        ['sudo', RABBITMQCTL, 'set_user_tags', username, 'administrator']
        )


def _ensure_rabbitmq_settings():
    """ Ensure rabbitmq settings (vhost, users) are correct. """
    _recreate_vhost('SSPL')
    _recreate_user('sspluser', 'sspl4ever', 'SSPL')


def _ensure_plex_running():
    with open('/dev/null', 'w') as devnull:
        status = subprocess.call(
            ['sudo', '/etc/init.d/plex', 'status'],
            stdout=devnull
            )

        if status != 0:
            subprocess.check_call(
                ['sudo', '/etc/init.d/plex', 'start'],
                stdout=devnull
                )


def _install_plex_apps():
    """ Install all relevant plex apps (currently just sspl_hl) """
    with open('/dev/null', 'w') as devnull:
        subprocess.check_call(
            ['sudo', 'rsync', '--recursive', './sspl_hl', '/opt/plex/apps/'],
            stdout=devnull
            )


def _disable_plex_auth():
    """ Disable plex's authentication.

    Note that plex is *not* restarted and that a restart is necessary if conf
    is changed.
    """
    status = subprocess.call([
        'sudo', 'grep', '-q', 'enable_plex_authentication=yes',
        '/etc/plex.config'
        ])
    if status != 0:
        return

    subprocess.call([
        'sudo', 'sed', '--in-place', '-e',
        's/enable_plex_authentication=yes/enable_plex_authentication=no/',
        '/etc/plex.config'
        ])


def _restart_plex():
    with open('/dev/null', 'w') as devnull:
        subprocess.check_call(
            ['sudo', '/etc/init.d/plex', 'restart'],
            stdout=devnull
            )


def _start_fake_halond():
    """ Starts the fake_halond process.

    Stores the process popen object into lettuce.world.fake_halond_process
    """
    if os.path.exists('/tmp/fake_halond') \
            or os.path.exists('/tmp/fake_halond.pid'):
        raise RuntimeError("Error: fake_halond already running?")

    lettuce.world.fake_halond_process = subprocess.Popen(
        ['./tests/fake_halond/fake_halond.py', '-p', '/tmp/fake_halond.pid']
        )

    lettuce.world.wait_for_condition(
        status_func=lambda: os.path.exists('/tmp/fake_halond'),
        max_wait=5,
        timeout_message="Timeout Expired waiting for fake_halond to start"
        )


@lettuce.before.all
def _start_frontier_service():
    """
    Starts a Frontier service
    Stores a process popen object into
    lettuce.world.frontier
    """
    lettuce.world.frontier = subprocess.Popen(
        ['./tests/fake_halond/frontier.py', '-p', '/tmp/frontier.pid']
    )


@lettuce.after.all
def _stop_frontier_service(_):
    """ Stops a frontier service
    """
    lettuce.world.frontier.terminate()
