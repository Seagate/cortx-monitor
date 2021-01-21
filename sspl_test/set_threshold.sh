#!/bin/bash

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

SCRIPT_DIR=$(dirname $0)
source "$SCRIPT_DIR"/constants.sh

SSPL_STORE_TYPE=confstor
sspl_config=$5

#Modify transmit_interval in $CONSUL_PATH/consul config less than current value
#to generate the alerts.
transmit_interval=$1
if [ "$SSPL_STORE_TYPE" == "file" ]
then
    [[ -f /etc/cortx/sspl.conf ]] && sed -i -e "s/\(transmit_interval: \).*/\1$transmit_interval/" /etc/cortx/sspl.conf
elif [ "$SSPL_STORE_TYPE" == "confstor" ]
then
    conf $sspl_config set "NODEDATAMSGHANDLER>transmit_interval=$transmit_interval"
else
    $CONSUL_PATH/consul kv put sspl/config/NODEDATAMSGHANDLER/transmit_interval $transmit_interval
fi

#Taking the current disk usage value and modify disk_usage_threshold in $CONSUL_PATH/consul config les than current value
#for generate the alerts.
#out=`python3.6 -c "import psutil; print(int(psutil.disk_usage('/')[3]-2))"`
out=$2
if [ "$SSPL_STORE_TYPE" == "file" ]
then
    [[ -f /etc/cortx/sspl.conf ]] && sed -i -e "s/\(disk_usage_threshold: \).*/\1$out/" /etc/cortx/sspl.conf
elif [ "$SSPL_STORE_TYPE" == "confstor" ]
then
    conf $sspl_config set "NODEDATAMSGHANDLER>disk_usage_threshold=$out"
else
    $CONSUL_PATH/consul kv put sspl/config/NODEDATAMSGHANDLER/disk_usage_threshold $out
fi

#Taking the current memory usage value and modify disk_usage_threshold in $CONSUL_PATH/consul config les than current value
#for generate the alerts.
#host_out=`python3.6 -c "import psutil; print((psutil.virtual_memory()[2]-2))"`
host_out=$3
if [ "$SSPL_STORE_TYPE" == "file" ]
then
    [[ -f /etc/cortx/sspl.conf ]] && sed -i -e "s/\(host_memory_usage_threshold: \).*/\1$host_out/" /etc/cortx/sspl.conf
elif [ "$SSPL_STORE_TYPE" == "confstor" ]
then
    conf $sspl_config set "NODEDATAMSGHANDLER>host_memory_usage_threshold=$host_out"
else
    $CONSUL_PATH/consul kv put sspl/config/NODEDATAMSGHANDLER/host_memory_usage_threshold $host_out
fi

#Taking the current cpu usage value and modify disk_usage_threshold in $CONSUL_PATH/consul config les than current value
#for generate the alerts.
#cpu_out=`python3.6 -c "import psutil; print((psutil.cpu_percent(interval=1, percpu=False)-5))"`
cpu_out=$4
if [ "$SSPL_STORE_TYPE" == "file" ]
then
    [[ -f /etc/cortx/sspl.conf ]] && sed -i -e "s/\(cpu_usage_threshold: \).*/\1$cpu_out/" /etc/cortx/sspl.conf
elif [ "$SSPL_STORE_TYPE" == "confstor" ]
then
    conf $sspl_config set "NODEDATAMSGHANDLER>cpu_usage_threshold=$cpu_out"
else
    $CONSUL_PATH/consul kv put sspl/config/NODEDATAMSGHANDLER/cpu_usage_threshold $cpu_out
fi