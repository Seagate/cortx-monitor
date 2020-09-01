# Copyright (c) 2017 Seagate Technology LLC and/or its Affiliates
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





class User(object):
    """Implementation of the user interface"""

    def __init__(self, username, pwd, authorizations=list()):
        self.username = username
        self.pwd = pwd
        self.authorizations = authorizations

    def __str__(self):
        """strigyfying the user object for pretty printing in JSON format
        NOTE: passwords will not be revealed out."""
        return dict(
            username=self.username,
            authorizations=self.authorizations
        ).__str__()
