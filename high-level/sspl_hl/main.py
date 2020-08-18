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

"""
Auto-generated PLEX application.
"""
# Third party
from zope.interface import implements
from twisted.plugin import IPlugin
# PLEX
from plex.common.interfaces.iapplication import IApplication
from plex.core.plex_application import PlexApplication
from plex.servicemaker.plex_dev_app_service_maker import dev_app_run_service


class Main(PlexApplication):  # pylint: disable=too-many-public-methods
    """The @string/title Application."""
    implements(IPlugin, IApplication)


# pylint: disable=invalid-name
main = Main("@string/title",
            "1.0",
            "@string/description",
            PlexApplication.CORE_APP)
# pylint: enable=invalid-name

if __name__ == "__main__":
    # Startup App Dev Mode
    dev_app_run_service()
