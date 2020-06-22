#!/bin/bash

SCRIPT_DIR=$(dirname $0)
. $SCRIPT_DIR/constants.sh

SSPL_STORE_TYPE=${SSPL_STORE_TYPE:-consul}

#Modify transmit_interval in /opt/seagate/<product>/hare/bin/consul config less than current value
#to generate the alerts.
transmit_interval=$1
if [ "$SSPL_STORE_TYPE" == "file" ]
then
    [[ -f /etc/sspl.conf ]] && sed -i -e "s/\(transmit_interval=\).*/\1$transmit_interval/" /etc/sspl.conf
else
    /opt/seagate/$PRODUCT_FAMILY/hare/bin/consul kv put sspl/config/NODEDATAMSGHANDLER/transmit_interval $transmit_interval
fi

#Taking the current disk usage value and modify disk_usage_threshold in /opt/seagate/<product>/hare/bin/consul config les than current value
#for generate the alerts.
#out=`python3.6 -c "import psutil; print(int(psutil.disk_usage('/')[3]-2))"`
out=$2
if [ "$SSPL_STORE_TYPE" == "file" ]
then
    [[ -f /etc/sspl.conf ]] && sed -i -e "s/\(disk_usage_threshold=\).*/\1$out/" /etc/sspl.conf
else
    /opt/seagate/$PRODUCT_FAMILY/hare/bin/consul kv put sspl/config/NODEDATAMSGHANDLER/disk_usage_threshold $out
fi

#Taking the current memory usage value and modify disk_usage_threshold in /opt/seagate/<product>/hare/bin/consul config les than current value
#for generate the alerts.
#host_out=`python3.6 -c "import psutil; print((psutil.virtual_memory()[2]-2))"`
host_out=$3
if [ "$SSPL_STORE_TYPE" == "file" ]
then
    [[ -f /etc/sspl.conf ]] && sed -i -e "s/\(host_memory_usage_threshold=\).*/\1$host_out/" /etc/sspl.conf
else
    /opt/seagate/$PRODUCT_FAMILY/hare/bin/consul kv put sspl/config/NODEDATAMSGHANDLER/host_memory_usage_threshold $host_out
fi

#Taking the current cpu usage value and modify disk_usage_threshold in /opt/seagate/<product>/hare/bin/consul config les than current value
#for generate the alerts.
#cpu_out=`python3.6 -c "import psutil; print((psutil.cpu_percent(interval=1, percpu=False)-5))"`
cpu_out=$4
if [ "$SSPL_STORE_TYPE" == "file" ]
then
    [[ -f /etc/sspl.conf ]] && sed -i -e "s/\(cpu_usage_threshold=\).*/\1$cpu_out/" /etc/sspl.conf
else
    /opt/seagate/$PRODUCT_FAMILY/hare/bin/consul kv put sspl/config/NODEDATAMSGHANDLER/cpu_usage_threshold $cpu_out
fi