"""
 ****************************************************************************
 Filename:          severity_reader.py
 Description:       Module to map severity against alert_type
 Creation Date:     11/13/2019
 Author:            Madhura Mande

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
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
