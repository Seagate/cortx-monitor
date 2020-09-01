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
  Description:       Module to map severity against alert_type
 ****************************************************************************
"""

class SeverityReader(object):

    ALERT_TO_SEVERITY_MAPPING = {
         "fault": "critical",
         "fault_resolved": "informational",
         "missing": "critical",
         "insertion": "informational",
         "threshold_breached:low": "warning",
         "threshold_breached:high": "warning"
    }

    def __init__(self):
        super(SeverityReader, self).__init__()

    def map_severity(self, alert_name):
        """Returns the severity by mapping it against the alert type"""
        try:
            severity = self.ALERT_TO_SEVERITY_MAPPING[alert_name]
            return severity
        except KeyError as e:
            raise Exception('SeverityReader, map_severity, No equivalent \
                            alert type found: %s' % e)
            return
        except Exception as e:
            logger.error('SeverityReader, map_severity, Exception occured \
                            while mapping alert_type to severity: %s ' % e)
            return
