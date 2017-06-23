#!/usr/bin/python
"""Tool for debugging purposes"""
import urllib
import json


def get_providers_list():
    """Returns all the providers that are installled"""
    provider_query = 'http://localhost:8080/registry/providers/'
    providers = json.loads(urllib.urlopen(url=provider_query).read())
    return json.dumps(providers, indent=4, sort_keys=True)

if __name__ == '__main__':
    print get_providers_list()
