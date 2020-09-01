#!/usr/bin/python

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
