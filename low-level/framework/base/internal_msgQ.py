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

"""
 ****************************************************************************
  Description:       Base class used for reading and writing to internal
                    message queues for modules to communication with one
                    another.
 ****************************************************************************
"""
from cortx.sspl.framework.utils.service_logging import logger

class InternalMsgQ(object):
    """Base Class for internal message queue communications between modules"""

    def __init__(self):
        super(InternalMsgQ, self).__init__()

    def initialize_msgQ(self, msgQlist):
        """Initialize the map of internal message queues"""
        self._msgQlist = msgQlist

    def _is_my_msgQ_empty(self):
        """Returns True/False for this module's queue being empty"""
        q = self._msgQlist[self.name()]
        return q.empty()

    def _read_my_msgQ(self):
        """Blocks on reading from this module's queue placed by another thread"""
        try:
            q = self._msgQlist[self.name()]
            jsonMsg, event = q.get()

            if jsonMsg is None:
                return None, None

            # Check for debugging being activated in the message header
            global_debug_off, jsonMsg = self._check_debug(jsonMsg)
            if global_debug_off is True:
                 self._debug_off_globally()

            self._log_debug("_read_my_msgQ: %s, Msg:%s" % (self.name(), jsonMsg))
            return jsonMsg, event

        except Exception as e:
            logger.exception("_read_my_msgQ: %r" % e)

        return None, None

    def _read_my_msgQ_noWait(self):
        """Non-Blocks on reading from this module's queue placed by another thread"""
        try:
            q = self._msgQlist[self.name()]

            # See if queue is empty otherwise don't bother
            if q.empty():
                return None, None

            # Don't block waiting for messages
            jsonMsg, event = q.get_nowait()

            if jsonMsg is None:
                return None, None

            # Check for debugging being activated in the message header
            global_debug_off, jsonMsg = self._check_debug(jsonMsg)
            if global_debug_off is True:
                self._debug_off_globally()

            self._log_debug("_read_my_msgQ_noWait: %s, Msg:%s" % (self.name(), jsonMsg))
            return jsonMsg, event

        except Exception as e:
            logger.exception("_read_my_msgQ_noWait: %r" % e)

    def _write_internal_msgQ(self, toModule, jsonMsg, event=None):
        """writes a json message to an internal message queue"""
        self._log_debug("_write_internal_msgQ: From %s, To %s, Msg:%s" %
                       (self.name(), toModule, jsonMsg))

        q = self._msgQlist[toModule]
        q.put((jsonMsg, event))

    def _get_msgQ_copy(self, module_name):
        """Returns a copy of a modules message queue"""
        with self._msgQlist[module_name].mutex:
           return list(self._msgQlist[module_name].queue)

    def _debug_off_globally(self):
        """Turns debug mode off on all threads"""
        jsonMsg = {'sspl_ll_debug': {'debug_component':'all', 'debug_enabled' : False}}
        for _msgQ in self._msgQlist:
            if _msgQ != "ThreadController":
                logger.info("_debug_off_globally, notifying: %s" % _msgQ)
                self._write_internal_msgQ(_msgQ, jsonMsg)

        # Notify the ThreadController to bounce all threads so that blocking ones switch debug mode
        jsonMsg = {'sspl_ll_debug': {'debug_component':'all'}}
        self._write_internal_msgQ("ThreadController", jsonMsg)
