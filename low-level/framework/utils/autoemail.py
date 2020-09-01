# Copyright (c) 2001-2020 Seagate Technology LLC and/or its Affiliates
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

# -*- coding: utf-8 -*-
"""
 ****************************************************************************
  Description:       Emailer Class to email logs to recipients as specified
                    in configuration file.
****************************************************************************
"""
import smtplib

from socket import gethostname, gethostbyaddr, gaierror
from socket import error as socket_error

try:
   from systemd import journal
   use_journal=True
except ImportError:
    use_journal=False

from syslog import (LOG_EMERG, LOG_ALERT, LOG_CRIT, LOG_ERR,
                    LOG_WARNING, LOG_NOTICE, LOG_INFO, LOG_DEBUG)

# Import the email modules we'll need
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


class AutoEmail(object):

    LOGLEVEL_NAME_TO_LEVEL_DICT = {
        "LOG_EMERG"   : LOG_EMERG,
        "LOG_ALERT"   : LOG_ALERT,
        "LOG_CRIT"    : LOG_CRIT,
        "LOG_ERR"     : LOG_ERR,
        "LOG_WARNING" : LOG_WARNING,
        "LOG_NOTICE"  : LOG_NOTICE,
        "LOG_INFO"    : LOG_INFO,
        "LOG_DEBUG"   : LOG_DEBUG
    }

    # Section and keys in configuration file
    SMTPSETTING = 'SMTPSETTING'
    SERVER      = 'smptserver'
    SENDER      = 'sender'
    RECIPIENT   = 'recipient'
    PRIORITY    = 'priority'

    LOGEMAILER    = 'LOGEMAILER'
    TLSSETTING    = 'smtp_port'
    SMTP_USERNAME = 'username'
    SMTP_PASSWORD = 'password'

    def __init__(self, conf_reader):
        super(AutoEmail, self).__init__()

        self._conf_reader = conf_reader
        self._configure_email()

        # First call gethostname() to see if it returns something that looks like a host name,
        # if not then get the host by address
        if gethostname().find('.') >= 0:
            self._email_sender = gethostname()
        else:
            self._email_sender = gethostbyaddr(gethostname())[0]

    def _configure_email(self):
        """Get SMTP Email settings from the conf file"""

        self._email_server = self._conf_reader._get_value_with_default(self.SMTPSETTING,
                                                             self.SERVER,
                                                             'mailhost.seagate.com')

        #Email recipients is a list
        self._email_recipient = self._conf_reader._get_value_list(self.SMTPSETTING,
                                                             self.RECIPIENT)
        #Get the priority from conf and map it to a number from 0-7, most to least critical
        self._log_priority = self.LOGLEVEL_NAME_TO_LEVEL_DICT[self._conf_reader._get_value_with_default(self.LOGEMAILER,
                                                             self.PRIORITY,
                                                             6)]

        #OPTIONAL SETTINGS:

        #SMTP Port settings
        self._tls_setting = self._conf_reader._get_value_with_default(self.SMTPSETTING,
                                                             self.TLSSETTING,
                                                             25)

        self._smtp_username = self._conf_reader._get_value_with_default(self.SMTPSETTING,
                                                             self.SMTP_USERNAME,
                                                             "")

        self._smtp_password = self._conf_reader._get_value_with_default(self.SMTPSETTING,
                                                             self.SMTP_PASSWORD,
                                                             "")


    def _send_email(self, message, msgPriority):
        """Sends an email depending on priority

        @param message = message to be sent
        @type message  = string

        @param msgPriority = priority of the message
        @type msgPriority = int

        @return : True -> Email successfully sent
                : False -> Email failed to send
        """
        if len(self._email_recipient) == 0:
            return "No email recipients in config file"

        if msgPriority > self._log_priority:
            priority     = "N/A"
            log_priority = "N/A"
            # Get the string values for displaying in logs
            for k, v in list(self.LOGLEVEL_NAME_TO_LEVEL_DICT.items()):
                if int(v) == msgPriority:
                    priority = k
                if int(v) == self._log_priority:
                    log_priority = k
            return "Not emailing due to: {0} not >= {1}". \
                        format(priority, log_priority)

        return_msg = "Failed to email log"
        try:
            # Create a connection with the SMTP server, timeout after 10 seconds
            mail = smtplib.SMTP(self._email_server, self._tls_setting, timeout=10)
            mail.ehlo()
            mail.starttls()

            # Set up the message to be sent
            msg = MIMEMultipart()
            msg['Subject'] = "Log Message"
            msg['From'] = self._email_sender
            msg['To'] = ", ".join(str(x) for x in self._email_recipient)   # List to string
            msg.attach(MIMEText(message, 'plain'))

            # Optional Username and Password authentication
            if len(self._smtp_username) > 0 and len(self._smtp_password) > 0:
                mail.login(self._smtp_username, self._smtp_password)

            # Send the email
            mail.sendmail(self._email_sender, self._email_recipient, msg.as_string())
            return_msg = "Emailed log successfully"

        # Errors that can occur at runtime
        except gaierror:
            if use_journal:
                journal.send("Could not get connection with server: {0}".format(self._email_server), PRIORITY=2)
        except socket_error:
            if use_journal:
                journal.send("Socket Error, port connection issue, port {0} used".format(self._tls_setting), PRIORITY=2)
        except smtplib.SMTPException:
            if use_journal:
                journal.send("SMTP Error", PRIORITY=2)
        except smtplib.SMTPServerDisconnected:
            if use_journal:
                journal.send("Server \'{0}\' unexpectedly disconnected".format(self._email_server), PRIORITY=2)
        except smtplib.SMTPResponseException:
            if use_journal:
                journal.send("SMTP Response error", PRIORITY=2)
        except smtplib.SMTPSenderRefused:
            if use_journal:
                journal.send("SMTP Refused sender: \'{0}\'".format(self._email_sender), PRIORITY=2)
        except smtplib.SMTPRecipientsRefused:
            if use_journal:
                journal.send("SMTP Refused recipients: \'{0}\'".format(", ".join(str(x) for x in self._email_recipient)), PRIORITY=2)
        except smtplib.SMTPDataError:
            if use_journal:
                journal.send("Server \'{0}\' refused message data".format(self._email_server), PRIORITY=2)
        except smtplib.SMTPConnectError:
            if use_journal:
                journal.send("Couldn't connect with the server: {0}".format(self._email_server), PRIORITY=2)
        except smtplib.SMTPHeloError:
            if use_journal:
                journal.send("Server \'{0}\' refused our HELO message".format(self._email_server), PRIORITY=2)
        except smtplib.SMTPAuthenticationError:
            if use_journal:
                journal.send("Authentication failed", PRIORITY=2)
        except Exception as e:
            if use_journal:
                journal.send("Unexpected error occured: {}".format(e), PRIORITY=2)

        finally:
            try:
                mail.quit()
            except Exception as e:
                if use_journal:
                    journal.send("Could not stop SMTP connection: Error: {}".format(e), PRIORITY=2)

        return return_msg
