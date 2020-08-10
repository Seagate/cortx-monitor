# -*- coding: utf-8 -*-
"""
 ****************************************************************************
 Filename:          autoemail.py
 Description:       Emailer Class to email logs to recipients as specified
                    in configuration file.
 Creation Date:     06/30/2015
 Author:            Andy Kim <jihoon.kim@seagate.com>
                    Alex Cordero <alexander.cordero@seagate.com>

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""
import smtplib

from socket import gethostname, gethostbyaddr, gaierror
from socket import error as socket_error
from framework.base.sspl_constants import SMTPSETTING, LOGEMAILER, SMRDRIVEDATA

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

        self._email_server = SMRDRIVEDATA.get("smptserver")

        #Email recipients is a list
        self._email_recipient = SMRDRIVEDATA.get("recipient")
        #Get the priority from conf and map it to a number from 0-7, most to least critical
        self._log_priority = self.LOGLEVEL_NAME_TO_LEVEL_DICT[LOGEMAILER.get("priority")]

        #OPTIONAL SETTINGS:

        #SMTP Port settings
        self._tls_setting = SMRDRIVEDATA.get("smtp_port")

        self._smtp_username = SMRDRIVEDATA.get("username")

        self._smtp_password = SMRDRIVEDATA.get("password")


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
