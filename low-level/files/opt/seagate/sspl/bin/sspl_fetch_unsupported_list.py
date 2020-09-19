#!/usr/bin/env python3

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

import subprocess
import ast
from cortx.utils.product_features import unsupported_features

storage_type = "virtual"
server_type = "virtual"
unsupported_feature_list = ["health"]
try:
    setup_info = subprocess.Popen(['sudo', 'provisioner', 'get_setup_info'],
        stdout=subprocess.PIPE).communicate()[0].decode("utf-8").rstrip()
    setup_info = ast.literal_eval(setup_info)
    storage_type = setup_info['storage_type'].lower()
    server_type = setup_info['server_type'].lower()
    print(f"Storage Type : '{storage_type}'")
    print(f"Server Type '{server_type}'")
    if (storage_type=="virtual") and (server_type=="virtual"):
        print("Unsupported features adding into unsupported feature Database.")
        unsupported_feature_instance = unsupported_features.UnsupportedFeaturesDB()
        unsupported_feature_instance.store_unsupported_features(component_name="sspl", features=unsupported_feature_list)
        print("Unsupported feature list added sucessfully.")
except Exception as err:
    print(f"Error in getting setup information : {err}")
    print(f"Considering default storage type : '{storage_type}'")
    print(f"Considering default server type : '{server_type}'")
