#! /bin/sh

target_dir='/opt/seagate/cortx/sspl/low-level/framework'

echo "Generating the coverage report.."
consul kv put sspl/config/SYSTEM_INFORMATION/log_level DEBUG
sleep 30s
timestamp=`stat /tmp/sspl/sspl_xml_coverage_report.xml | grep Modify | cut -d ' ' -f2,3`
echo "${timestamp} : The report is saved at /tmp/sspl/sspl_xml_coverage_report.xml"

echo "Stoping sspl-ll for resetting the sspl environment"
systemctl stop sspl-ll.service

ln -sf $target_dir/sspl_ll_d /usr/bin/sspl_ll_d

sudo rm $target_dir/sspl_ll_d_coverage

consul kv put sspl/config/SYSTEM_INFORMATION/log_level INFO

echo "Normal sspl environment is set staring the sspl-ll.service"
systemctl start sspl-ll.service
echo "Done."
