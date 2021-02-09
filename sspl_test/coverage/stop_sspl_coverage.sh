#! /bin/sh

target_dir='/opt/seagate/cortx/sspl/low-level'

echo "Generating the coverage report.."
systemctl --kill-who=main kill -s SIGUSR1 sspl-ll.service
sleep 20s
timestamp=$(stat /tmp/sspl/sspl_xml_coverage_report.xml | grep Modify | cut -d ' ' -f2,3)
echo "${timestamp} : The report is saved at /tmp/sspl/sspl_xml_coverage_report.xml"

echo "Stoping sspl-ll for resetting the sspl environment"
systemctl stop sspl-ll.service

sudo rm $target_dir/sspl_ll_d
sudo mv $target_dir/sspl_ll_d.back $target_dir/sspl_ll_d

echo "Normal sspl environment is set staring the sspl-ll.service"
systemctl start sspl-ll.service
echo "Done."
