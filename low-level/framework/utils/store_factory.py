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

import os
import sys
from configparser import ConfigParser

from framework.utils.filestore import FileStore
from framework.utils.consulstore import ConsulStore
from framework.base.sspl_constants import StoreTypes, SSPL_STORE_TYPE, CONSUL_HOST, CONSUL_PORT, file_store_config_path


class StorFactory:

    __store = None

    @staticmethod
    def get_store():
        if StorFactory.__store == None:
            try:
                store_type = os.getenv('SSPL_STORE_TYPE', SSPL_STORE_TYPE)
                if store_type == StoreTypes.FILE.value:
                    StorFactory.__store = FileStore()
                    StorFactory.__store.read(file_store_config_path)
                elif store_type == StoreTypes.CONSUL.value:
                    host = os.getenv('CONSUL_HOST', CONSUL_HOST)
                    port = os.getenv('CONSUL_PORT', CONSUL_PORT)
                    StorFactory.__store = ConsulStore(host, port)
                else:
                    raise Exception("{} type store is not supported".format(store_type))

                return StorFactory.__store
            except Exception as serror:
                print("Error in connecting either with file or consul store: {}".format(serror))
                print("Exiting ...")
                sys.exit(os.EX_USAGE)
        return StorFactory.__store

store=StorFactory.get_store()
