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

#Taking the current disk usage value and modify disk_usage_threshold in /etc/sspl.conf les than current value
#for generate the alerts.
out=`python -c "import psutil; print int(psutil.disk_usage('/')[3]-2)"`
sed -i -e "s/\(disk_usage_threshold=\).*/\1$out/" /etc/sspl.conf

#Taking the current memory usage value and modify disk_usage_threshold in /etc/sspl.conf les than current value
#for generate the alerts.
host_out=`python -c "import psutil; print (psutil.virtual_memory()[2]-2)"`
sed -i -e "s/\(host_memory_usage_threshold=\).*/\1$host_out/" /etc/sspl.conf

#Taking the current cpu usage value and modify disk_usage_threshold in /etc/sspl.conf les than current value
#for generate the alerts.
cpu_out=`python -c "import psutil; print (psutil.cpu_percent(interval=1, percpu=False)-5)"`
cpu_out="1"
sed -i -e "s/\(cpu_usage_threshold=\).*/\1$cpu_out/" /etc/sspl.conf
