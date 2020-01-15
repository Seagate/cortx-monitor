#!/bin/bash
#Taking the current disk usage value and modify disk_usage_threshold in /etc/sspl.conf les than current value
#for generate the alerts.
out=`python3.6 -c "import psutil; print(int(psutil.disk_usage('/')[3]-2))"`
sed -i -e "s/\(disk_usage_threshold=\).*/\1$out/" /etc/sspl.conf

#Taking the current memory usage value and modify disk_usage_threshold in /etc/sspl.conf les than current value
#for generate the alerts.
host_out=`python3.6 -c "import psutil; print((psutil.virtual_memory()[2]-2))"`
sed -i -e "s/\(host_memory_usage_threshold=\).*/\1$host_out/" /etc/sspl.conf

#Taking the current cpu usage value and modify disk_usage_threshold in /etc/sspl.conf les than current value
#for generate the alerts.
cpu_out=`python3.6 -c "import psutil; print((psutil.cpu_percent(interval=1, percpu=False)-5))"`
cpu_out="1"
sed -i -e "s/\(cpu_usage_threshold=\).*/\1$cpu_out/" /etc/sspl.conf
