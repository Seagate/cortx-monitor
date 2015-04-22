#!/usr/bin/env python2.7
""" cstor cli command.

Run ./cstor --help (or ./cstor <subcommand> --help) for usage details.
"""
import argparse
import sys
import urllib
import json


def main(args=sys.argv[1:]):
    """ cstor mainline. """
    parser = argparse.ArgumentParser(
        description="cstor cli.  See individual command's --help output for "
        "details."
        )
    subparsers = parser.add_subparsers()
    service_parser = subparsers.add_parser(
        'service',
        help='Subcommand to work with services on the cluster.'
        )
    service_parser.set_defaults(func=service)
    service_parser.add_argument(
        'command',
        help="Command to run.",
        choices=['start', 'stop', 'restart', 'enable', 'disable', 'status']
        )
    service_parser.add_argument(
        'service_name',
        help="Service to operate on.  eg crond.",
        )
    #service_parser.add_argument(
    #    'node_spec',
    #    help="Optional parameter to indicate which nodes should be affected.",
    #    nargs='?'
    #    )

    args = parser.parse_args(args)
    args.func(args)


def _get_service_provider_base_uri():
    providers = json.loads(
        urllib.urlopen(url="http://localhost:8080/registry/providers").read()
        )
    try:
        return next(
            provider
            for provider in providers
            if provider['application'] == 'sspl_hl'
            and provider['name'] == 'service'
            )['uri']
    except StopIteration:
        raise RuntimeError(
            "Unable to find the sspl_hl.service provider on localhost:8080"
            )


def service(args):
    """ service subcommand implementation. """
    url = "http://{host}{service_provider}data?{params}".format(
        host="localhost:8080",
        service_provider=_get_service_provider_base_uri(),
        params="serviceName={service}&command={cmd}".format(
            service=args.service_name,
            cmd=args.command
            )
        )

    urllib.urlopen(url=url)
    print "Request to {command} {service} sent.".format(
        command=args.command,
        service=args.service_name
        )


if __name__ == '__main__':
    main()
