#!/bin/bash
#
# Copyright (c) 2020 Seagate Technology LLC and/or its Affiliates
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
# For any questions about this software or licensing,
# please email opensource@seagate.com or cortx-questions@seagate.com.
#


# *******************************************************************
#  Description:   SSPL prerequisites script to setup environment
#  Purpose    :   Setup yum repos, consul and rabbitmq for SSPL
#  Usage      :   ./sspl_dev_deploy.sh --help
# *******************************************************************

set -eE

CORTX_MONITOR_BASE_URL="https://raw.githubusercontent.com/mariyappanp/cortx-monitor/EOS-15396_self_prv"
SSPL_BASE_DIR="/opt/seagate/cortx/sspl"

LOG_FILE="${LOG_FILE:-/var/log/cortx/sspl/sspl_dev_deploy.log}"
export LOG_FILE

if [[ ! -e "$LOG_FILE" ]]; then
    mkdir -p $(dirname "${LOG_FILE}")
fi

# Config file to store cluster_id & node_id
PERSISTENT_CONFIG_FILE="/opt/seagate/cortx/sspl/generated_configs"
if [[ ! -e "$PERSISTENT_CONFIG_FILE" ]]; then
    mkdir -p $(dirname "$PERSISTENT_CONFIG_FILE")
    touch $PERSISTENT_CONFIG_FILE
fi

echo "INFO: ******** Running $0  ********" 2>&1 | tee -a "${LOG_FILE}"
echo "INFO: Date: $(date)" 2>&1 | tee -a "${LOG_FILE}"

do_cleanup=false
install_3rd_party_packages=false
setup_repo=false
skip_bmc=false
initialize_sspl=false
TARGET_BUILD=
RPMS_PATH=
PRODUCT_VERSION="LDR_R2"
NODE="srvnode-1"
RMQ_USER="sspluser"
RMQ_PASSWD="xxxx"
CNTRLR_A="10.0.0.2"
CNTRLR_B="10.0.0.3"
CNTRLR_A_PORT="80"
CNTRLR_B_PORT="80"
CNTRLR_USER="manage"
CNTRLR_PASSWD="xxxx"
BMC_IP=""
BMC_USER=""
BMC_PASSWD="xxxx"
SERVER_TYPE="virtual"
STORAGE_TYPE="virtual"


usage()
{
    echo "\
    SSPL prerequisite script.
    (Bounded to single node provisioning)

    Usage:
         $0
            [-V|--product_version  <LDR_R2>]
            [-N|--node  <Node name/id>]
            [-A|--cntrlr_a  <controller A IP>]
            [-B|--cntrlr_b  <controller B IP>]
            [-L|--local_rpms_path   <sspl rpms location>]
            [-T|--target_build_url  <target build url>]
            [--Ap|--cntrlr_a_port  <controller A Port>]
            [--Bp|--cntrlr_b_port  <controller B Port>]
            [-U|--cntrlr_user   <username>]
            [-P|--cntrlr_pass   <password>]
            [--i|--bmc_ip     <bmc ipv4 address>]
            [--u|--bmc_user   <bmc user>]
            [--p|--bmc_passwd <bmc password>]
            [--Ru|--rmq_user    <rabbitmq username>]
            [--Rp|--rmq_passwd  <rabbitmq password>]
            [--St|--storage_type  <storage type>]
            [--Sr|--server_type    <server type>]
            [--standalone_installation]
            [--initialize_sspl]
            [--setup_repo]
            [--cleanup]
            [-h|--help]

    OPTION:
    -V      <PRODUCT VERSION>   Product version (Default 'LDR_R2')
    -N      <NODE NAME>         Default 'srvnode-1'
    -A      <IP ADDRESS>        IP address of controller A (default '10.0.0.2')
    -B      <IP ADDRESS>        IP address of controller B (default '10.0.0.3')
    --Ap    <CNTRLR A PORT>     Controller A port (default '80')
    --Bp    <CNTRLR A PORT>     Controller B port (default '80')
    -U      <USER NAME>         Username for controller (default 'manage')
    -P      <PASSWORD>          Password for controller
    --Ru    <RMQ USER>          Username for Rabbitmq (default 'sspluser')
    --Rp    <RMQ PASSWORD>      Password for Rabbitmq
    --i     <BMC IP>            BMC IPV4 for Node-1 (default '')
    --u     <BMC USER>          BMC User for Node-1 (default '')
    --p     <BMC PASSWORD>      BMC Password for node (default '')
    -L      <LOCAL RPMS PATH>   Local RPMS location
    -T      <TARGET BUILD>      Target build base url pointed to release bundle base directory,
                if specified the following directory structure is assumed:
                <base_url>/
                    centos7.7   <- OS ISO is mounted here
                    3rd_party   <- CORTX 3rd party ISO is mounted here
                    cortx_iso   <- CORTX ISO (main) is mounted here
    --standalone_installation   Configure SSPL 3rd party dependencies like consul, rabbitmq
    --initialize_sspl           Initialize SSPL
    --setup_repo                Setup yum repos
    --St    <STORAGE TYPE>      Storage type  ie. jbod, rbod, 5u84, virtual
    --Sr    <SERVER TYPE>       Server type   ie. physical, virtual
    --cleanup                   Stop sspl-ll and remove installed SSPL RPMs
    "
    exit 0
}

parse_args()
{
    while [[ $# -gt 0 ]]; do
        case "$1" in
        -h|--help)
            usage ;;
        --cleanup)
            do_cleanup=true
            shift ;;
        --standalone_installation)
            install_3rd_party_packages=true
            shift ;;
        --initialize_sspl)
            initialize_sspl=true
            shift ;;
        --setup_repo)
            setup_repo=true
            shift ;;
        -V|--product_version)
            [ -z "$2" ] && echo "ERROR: Product version(LDR_R1/LDR_R2) not provided" && exit 1;
            PRODUCT_VERSION="$2"
            shift 2 ;;
        -N|--node)
            [ -z "$2" ] && echo "ERROR: Node name not provided" && exit 1;
            NODE="$2"
            shift 2 ;;
        --Ru|--rmq_user)
            [ -z "$2" ] && echo "ERROR: Rabbitmq user not provided" && exit 1;
            RMQ_USER="$2"
            shift 2 ;;
        --Rp|--rmq_passwd)
            [ -z "$2" ] && echo "ERROR: Rabbitmq password not provided" && exit 1;
            RMQ_PASSWD="$2"
            shift 2 ;;
        -A|--cntrlr_a)
            [ -z "$2" ] && echo "ERROR: Controller A IP not provided" && exit 1;
            CNTRLR_A="$2"
            shift 2 ;;
        --Ap|--cntrlr_a_port)
            [ -z "$2" ] && echo "ERROR: Controller A Port not provided" && exit 1;
            CNTRLR_A_PORT="$2"
            shift 2 ;;
        -B|--cntrlr_b)
            [ -z "$2" ] && echo "ERROR: Controller B IP not provided" && exit 1;
            CNTRLR_B="$2"
            shift 2 ;;
        --Bp|--cntrlr_b_port)
            [ -z "$2" ] && echo "ERROR: Controller B Port not provided" && exit 1;
            CNTRLR_B_PORT="$2"
            shift 2 ;;
        -U|--cntrlr_user)
            [ -z "$2" ] && echo "ERROR: Controller user name not provided" && exit 1;
            CNTRLR_USER="$2"
            shift 2 ;;
        -P|--cntrlr_pass)
            [ -z "$2" ] && echo "ERROR: Controller password not provided" && exit 1;
            CNTRLR_PASSWD="$2"
            shift 2 ;;
        -T|--target_build_url)
            [ -z "$2" ] && echo "ERROR: Target build not provided" && exit 1;
            TARGET_BUILD="$2"
            shift 2 ;;
        -L|--local_rpms_path)
            [ -z "$2" ] && echo "ERROR: Local RPMS not provided" && exit 1;
            RPMS_PATH="$2"
            shift 2 ;;
        --i|--bmc_ip)
            [ -z "$2" ] && echo "ERROR: BMC IP not provided" && exit 1;
            BMC_IP="$2"
            shift 2 ;;
        --u|--bmc_user)
            [ -z "$2" ] && echo "ERROR: BMC user not provided" && exit 1;
            BMC_USER="$2"
            shift 2 ;;
        --p|--bmc_passwd)
            [ -z "$2" ] && echo "ERROR: BMC password not provided" && exit 1;
            BMC_PASSWD="$2"
            shift 2 ;;
        --St|--storage_type)
            [ -z "$2" ] && echo "ERROR: Storage type not provided" && exit 1;
            STORAGE_TYPE="$2"
            shift 2 ;;
        --Sr|--server_type)
            [ -z "$2" ] && echo "ERROR: Server type not provided" && exit 1;
            SERVER_TYPE="$2"
            shift 2 ;;
        *)
            echo "ERROR: Unknown option provided: $1"
            exit 1 ;;
        esac
    done
}

parse_args "$@"

# Cleanup
[ "$do_cleanup" == "true" ] && {
    systemctl stop sspl-ll ||:
    yum remove -y cortx-sspl.noarch
    exit ;
}


# Setup common, 3rd_party and build specific repos
[ "$setup_repo" == true ] && {
    curl ${CORTX_MONITOR_BASE_URL}/low-level/files/opt/seagate/sspl/bin/setup_yum_repos.sh -o setup_yum_repos.sh
    chmod a+x setup_yum_repos.sh

    if [ -n "$TARGET_BUILD" ]; then
        ./setup_yum_repos.sh -t $TARGET_BUILD 2>&1 | tee -a "${LOG_FILE}"
    else
        ./setup_yum_repos.sh 2>&1 | tee -a "${LOG_FILE}"
    fi

    echo -e "\nDone setup repos" 2>&1 | tee -a "${LOG_FILE}"
    exit ;
}


if [ "$PRODUCT_VERSION" == "LDR_R2" ] &&  [ -z "$BMC_IP" ]
then
    skip_bmc=true
    echo "Skipping BMC information for LDR_R2..." 2>&1 | tee -a "${LOG_FILE}" ;
else
    [ -z "$BMC_IP" ] && echo "ERROR: --i <BMC IPV4> is required." && exit 1;
    [ -z "$BMC_USER" ] && echo "ERROR: --u <BMC user> is required." && exit 1;
    [ -z "$BMC_PASSWD" ] && echo "ERROR: --p <BMC password> is required." && exit 1;
fi


# Install required RPMS if not available
"$install_3rd_party_packages" && {

    echo "INFO: INSTALLING python3..." 2>&1 | tee -a "${LOG_FILE}"
    yum install -y python3 2>&1 | tee -a "${LOG_FILE}"

    echo "INFO: INSTALLING cortx-py-utils..." 2>&1 | tee -a "${LOG_FILE}"
    # yum install -y cortx-py-utils 2>&1 | tee -a "${LOG_FILE}"
    # TODO: When RE brings main branch as same strucure as cortx_builds,
    # below shoudl be rmeoved and setup_yum_repo should be able to give cortx-py-utils.
    pkg_name="cortx-py-utils"
    build_url="http://cortx-storage.colo.seagate.com/releases/cortx/github/main/centos-7.8.2003/cortx-utils_last_successful/"
    yum install -y $build_url/$(curl -s $build_url/|grep $pkg_name|sed 's/<\/*[^"]*"//g'|cut -d"\"" -f1) ||:

    echo "INFO: INSTALLING rabbitmq-server..." 2>&1 | tee -a "${LOG_FILE}"
    yum install -y rabbitmq-server 2>&1 | tee -a "${LOG_FILE}"

}


# If local RPMS location is specified, SSPL RPMS will be
# installed from the speicifed path. Otherwise yum repos.
install_sspl_rpms(){
    if [ -n "$RPMS_PATH" ]; then
        echo -e "INFO: Installing SSPL RPMS from local path - ${RPMS_PATH}"
        sudo yum localinstall -y $RPMS_PATH/cortx-libsspl_sec-2* \
                            $RPMS_PATH/cortx-libsspl_sec-method_none-2* \
                            $RPMS_PATH/cortx-sspl-2* \
                            $RPMS_PATH/cortx-sspl-test-2*
    else
        echo "INFO: Installing SSPL RPMS using yum repos..."
        yum install -y cortx-sspl.noarch
        yum install -y cortx-sspl-test
    fi
    echo "Done installing SSPL RPMS.";

    python3 -m pip install -r ${SSPL_BASE_DIR}/low-level/requirements.txt
}


update_sspl_config(){

    # update sspl config file
    SSPL_CONF="/etc/sspl.conf"
    SOURCE_CONF=${SSPL_BASE_DIR}/low-level/files/opt/seagate/sspl/conf/sspl.conf.${PRODUCT_VERSION}
    cp $SOURCE_CONF $SSPL_CONF

    CONFIG_FEEDER=$SSPL_BASE_DIR/low-level/files/opt/seagate/sspl/bin/update_sspl_config.py

    echo "INFO: Updating $SSPL_CONF config file.."
    if [ "$skip_bmc" == "true" ];
    then
        python3 $CONFIG_FEEDER -N $NODE -C $SSPL_CONF \
                -Ru $RMQ_USER -Rp $RMQ_PASSWD \
                -A $CNTRLR_A -Ap $CNTRLR_A_PORT -B $CNTRLR_B -Bp $CNTRLR_B_PORT \
                -U $CNTRLR_USER -P $CNTRLR_PASSWD \
                -St $STORAGE_TYPE -Sr $SERVER_TYPE ;
    else
        python3 $CONFIG_FEEDER -N $NODE -C $SSPL_CONF  \
                -Ru $RMQ_USER -Rp $RMQ_PASSWD \
                -A $CNTRLR_A -Ap $CNTRLR_A_PORT -B $CNTRLR_B -Bp $CNTRLR_B_PORT \
                -U $CNTRLR_USER -P $CNTRLR_PASSWD \
                -St $STORAGE_TYPE -Sr $SERVER_TYPE \
                --bmc_ip $BMC_IP --bmc_user $BMC_USER --bmc_passwd $BMC_PASS ;
    fi

}


setup_rabbitmq(){

    # Start rabbitmq
    systemctl status rabbitmq-server 1>/dev/null && export status=true || export status=false
    if [ "$status" = "false" ]; then
        systemctl start rabbitmq-server
    fi

    RMQ_REINIT=$SSPL_BASE_DIR/low-level/framework/sspl_rabbitmq_reinit
    python3 $RMQ_REINIT $PRODUCT_VERSION || {
        reinit_err="$?"
        echo -n "ERROR: sspl_rabbitmq_reinit failed "
        echo "with exit code ${reinit_err} for product $PRODUCT_VERSION"
        exit 1
    }
    $SSPL_BASE_DIR/bin/setup_rabbitmq_cluster
    echo "Done rabbitmq setup.";

}


setup_sspl(){

    [ "$initialize_sspl" == true ] &&
        /opt/seagate/cortx/sspl/bin/sspl_setup setup -p $PRODUCT_VERSION

}


# Install SSPL
install_sspl_rpms 2>&1 | tee -a "${LOG_FILE}"

# Insert config in consul
update_sspl_config 2>&1 | tee -a "${LOG_FILE}"

# Configure rabbitmq-server
setup_rabbitmq 2>&1 | tee -a "${LOG_FILE}"

# Configure SSPL
setup_sspl 2>&1 | tee -a "${LOG_FILE}"


echo "For more details see: $LOG_FILE"
echo -e "\n***** COMPLETED!!! *****" 2>&1 | tee -a "${LOG_FILE}"
