# Copyright (c) 2019-2020 Seagate Technology LLC and/or its Affiliates
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
 ****************************************************************************
  Description:       Common utility functions required for monitoring purpose
 ****************************************************************************
"""

import uuid
from cortx.utils.log import Log as logger


class MonUtils():
    """Base class for all the monitor utilities."""
    def __init__(self):
        """Init method."""
        super(MonUtils, self).__init__()

    @staticmethod
    def get_alert_id(epoch_time):
        """Returns alert id which is a combination of
            epoch_time and salt value
        """
        salt = str(uuid.uuid4().hex)
        alert_id = epoch_time + salt
        return alert_id

    @staticmethod
    def normalize_kv(item, input_v, replace_v):
        """Normalize all values coming from input as per requirement."""
        if isinstance(item, dict):
            return {key: MonUtils.normalize_kv(value, input_v, replace_v)
                for key, value in item.items()}
        elif isinstance(item, list):
            return [MonUtils.normalize_kv(_, input_v, replace_v) for _ in item]
        elif item in input_v if isinstance(input_v, list) else item == input_v:
            return replace_v
        else:
            return item

    @staticmethod
    def sort_by_specific_kv(data, key_path, log):
        """
        Accept list of dictionary and sort by key value.
        data: list of dictionary
               Examples:
                    [{},{}]
        key_path: Sort list on the basis of the key path.
               Examples:
                    '["health"]["specifics"][0]["serial-number"]'
        log: log object.
        """
        sorted_data = []
        try:
            if key_path and data:
                sorted_data = sorted(data, key=lambda k: eval(f'{k}{key_path}'))
            else:
                sorted_data = data
        except Exception as err:
            sorted_data = data
            msg = 'Key: %s not found in data: %s for sorting: %s"' % (
                key_path, data, err)
            logger.error(log.svc_log(f"{msg}"))
        return sorted_data
