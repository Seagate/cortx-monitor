# CORTX Python common library.
# Copyright (c) 2021 Seagate Technology LLC and/or its Affiliates
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
# For any questions about this software or licensing,
# please email opensource@seagate.com or cortx-questions@seagate.com

from framework.platforms.server.hba import HBA


class ServerCompFactory(object):
    """"Returns instance of a specific component class from the factory."""

    components = {}

    @staticmethod
    def get_instance(component):
        """
        Returns the instance of server component by iterating globals
        dictionary.
        """
        if component not in ServerCompFactory.components.keys():
            for key, _ in globals().items():
                if key.lower() == component.lower():
                    ServerCompFactory.components[component] = globals()[key]()
                    break
        return ServerCompFactory.components[component]
