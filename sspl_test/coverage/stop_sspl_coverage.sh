#! /bin/sh

target_dir='/opt/seagate/cortx/sspl/low-level'

echo "Generating the coverage report.."
systemctl --kill-who=main kill -s SIGUSR1 sspl-ll.service
sleep 5s
timestamp=$(stat /var/cortx/sspl/coverage/sspl_xml_coverage_report.xml | grep Modify | cut -d ' ' -f2,3)
echo "${timestamp} : The Code Coverage report is saved at /var/cortx/sspl/coverage/sspl_xml_coverage_report.xml"

sudo rm $target_dir/sspl_ll_d
sudo mv $target_dir/sspl_ll_d.back $target_dir/sspl_ll_d
