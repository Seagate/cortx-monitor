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

# This script contains common constants used by various provisioner scripts

PRODUCT_NAME='LDR_R2'
PRODUCT_FAMILY='cortx'
PRODUCTS="SINGLE DUAL CLUSTER LDR_R1 LDR_R2"
SSPL_CONF="/etc/sspl.conf"
ROLES="gw ssu vm cmu cortx"
PRODUCT_BASE_DIR="/opt/seagate/$PRODUCT_FAMILY/"
SSPL_BASE_DIR="/opt/seagate/$PRODUCT_FAMILY/sspl"
SSPL_STORE_TYPE="consul"
CONSUL_HOST="127.0.0.1"
CONSUL_PORT="8500"
ENVIRONMENT="PROD"
CONSUL_PATH="/usr/bin/"
# This file will be created when sspl is being configured for node replacement case
REPLACEMENT_NODE_ENV_VAR_FILE="/etc/profile.d/set_replacement_env.sh"
