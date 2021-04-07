 #! /bin/sh
echo "Checking and installing coverage.py"
pip3_status=$(which pip3)
pip_status=$(which pip)
if [[ $pip3_status =~ "/bin/pip3" ]]
then 
    pip3 install coverage
elif [[$pip_status =~ "/bin/pip"]]
then
    pip install coverage
fi

echo "Creating required files for coverage.."
target_dir='/opt/seagate/cortx/sspl/low-level'
cov_code_dir='/opt/seagate/cortx/sspl/sspl_test/coverage'

sudo cp $target_dir/sspl_ll_d $target_dir/sspl_ll_d_coverage

copy_lines() {
    for line_num in `seq $1 $2` 
    do 
        str=`sed $((line_num))!d $cov_code_dir/coverage_code`; fix='\';
        str="${fix}${str}";
        curr_line=$((curr_line+1));
        sed -i "$curr_line i $str" $target_dir/sspl_ll_d_coverage;
    done    
}

curr_line=`grep -n "#DO NOT EDIT: Marker comment to dynamically add code to initialize coverage obj for code coverage report generation" $target_dir/sspl_ll_d_coverage | cut -d : -f1`
copy_lines 1 7

curr_line=`grep -n "#DO NOT EDIT: Marker comment to dynamically add code to start the code coverage scope" $target_dir/sspl_ll_d_coverage | cut -d : -f1`
copy_lines 8 9

curr_line=`grep -n "#DO NOT EDIT: Marker comment to dynamically add code to stop coverage, save and generate code coverage report" $target_dir/sspl_ll_d_coverage | cut -d : -f1`
copy_lines 10 24

curr_line=`grep -n "#DO NOT EDIT: Marker comment to dynamically add signal handler for SIGUSR1 to generate code coverage report" $target_dir/sspl_ll_d_coverage | cut -d : -f1`
copy_lines 25 25

echo "Changing existing sspl_ll_d file and creating and "\
"adding permission for /var/cortx/sspl/coverage/ folder"

sudo mv $target_dir/sspl_ll_d $target_dir/sspl_ll_d.back
sudo mv $target_dir/sspl_ll_d_coverage $target_dir/sspl_ll_d

mkdir -p /var/cortx/sspl/coverage/
chmod 755 /var/cortx/sspl/coverage/* 
chown sspl-ll:sspl-ll /var/cortx/sspl/coverage/ -R
