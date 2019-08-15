#!/bin/bash

out=`python -c "import psutil; print int(psutil.disk_usage('/')[3]-2)"`
sudo sed -i -e "s/\(disk_usage_threshold=\).*/\1$out/" /etc/sspl.conf
