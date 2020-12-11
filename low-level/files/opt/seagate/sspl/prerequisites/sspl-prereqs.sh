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


set -eE

script_dir=$(dirname $0)

LOG_FILE="${LOG_FILE:-/var/log/cortx/sspl/sspl-prereqs.log}"
export LOG_FILE

if [[ ! -e "$LOG_FILE" ]]; then
    mkdir -p $(dirname "${LOG_FILE}")
fi

echo "***************************************" | tee -a ${LOG_FILE}
echo "DATE: $(date)" 2>&1 | tee -a ${LOG_FILE}
echo "SCRIPT: $(basename $0)" 2>&1 | tee -a ${LOG_FILE}

do_cleanup=false
install_3rd_party_packages=false
disable_sub_mgr=false
TARGET_BUILD=
COMPONENT=sspl
SSPL_VERSION="LDR_R2"
NODE='srvnode-1'
CNTRLR_A="10.0.0.2"
CNTRLR_B="10.0.0.3"
CNTRLR_USER="manage"
ENVIRONMENT="PROD"


usage()
{
    echo "\
    SSPL prerequisite script.
    (Bounded to single node provisioning)

    Usage:
         $0
            [-V|--sspl_version  <LDR_R1, LDR_R2>]
            [-E|--env   <environment>]
            [-N|--node  <Node name/id>]
            [-A|--cntrlr_a  <controller A IP>]
            [-B|--cntrlr_b  <controller B IP>]
            [--Ap|--cntrlr_a_port  <controller A Port>]
            [--Bp|--cntrlr_b_port  <controller B Port>]
            [-U|--cntrlr_user   <username>]
            [-P|--cntrlr_pass   <password>]
            [-R|--rpmq_pass    <rabbitmq password>]
            [-T|--taregt_build  <target build url>]
            [--i|--bmc_ip   <bmc ip>]
            [--u|--bmc_user   <bmc user>]
            [--p|--bmc_pass   <bmc password>]
            [--disable-sub-mgr]
            [--standalone-installation]
            [--cleanup]
            [-h|--help]

    OPTION:
    -V      <SSPL VERSION>   SSPL product version (LDR_R1 | LDR_R2)
    -E      <ENVIRONMENT>    Environment type (PROD | DEV)
    -N      <NODE NAME>      Default 'srvnode-1'
    -A      <IP ADDRESS>     IP address of controller A (default 10.0.0.2)
    -B      <IP ADDRESS>     IP address of controller B (default 10.0.0.3)
    --Ap    <CNTRLR A PORT>  Controller A port
    --Bp    <CNTRLR A PORT>  Controller B port
    -U      <USER NAME>      Username for controller
    -P      <PASSWORD>       Password for controller (Encrypted)
    -R      <RPMQ Password>  Password for Rabbitmq (Encrypted)
    --i     <BMC IP>         BMC IP for Node-1
    --u     <BMC USER>       BMC User for Node-1
    --p     <BMC PASSWORD>   BMC Password for Node-1 (Encrypted)
    -T      Target build base url pointed to release bundle base directory,
            if specified the following directory structure is assumed:
            <base_url>/
                rhel7.7 or centos7.7   <- OS ISO is mounted here
                3rd_party              <- CORTX 3rd party ISO is mounted here
                cortx_iso              <- CORTX ISO (main) is mounted here
    --standalone_installation       Configure SSPL 3rd party dependencies like consul, rabbitmq
    --disable-sub-mgr       For RHEL. To install prerequisites by disabling
                            subscription manager (usually, not recommended).
                            If this option is not provided it is expected that
                            either the system is not RHEL or system is already
                            registered with subscription manager
    --cleanup       Remove dependencies
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
        --disable-sub-mgr)
            disable_sub_mgr=true
            shift ;;
        --standalone-installation)
            install_3rd_party_packages=true
            shift ;;
        -V|--sspl_version)
            [ -z "$2" ] && echo "ERROR: SSPL version(LDR_R1/LDR_R2) not provided" && exit 1;
            SSPL_VERSION="$2"
            shift 2 ;;
        -E|--env)
            [ -z "$2" ] && echo "ERROR: Environment not provided" && exit 1;
            ENVIRONMENT="$2"
            shift 2 ;;
        -N|--node)
            [ -z "$2" ] && echo "ERROR: Node name not provided" && exit 1;
            NODE="$2"
            shift 2 ;;
        -R|--rpmq_pass)
            [ -z "$2" ] && echo "ERROR: Rabbitmq password not provided" && exit 1;
            RPMQ_PASS="$2"
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
            CNTRLR_PASS="$2"
            shift 2 ;;
        -T|--taregt_build)
            [ -z "$2" ] && echo "ERROR: Target build not provided" && exit 1;
            TARGET_BUILD="$2"
            shift 2 ;;
        --i|--bmc_ip)
            [ -z "$2" ] && echo "ERROR: BMC IP not provided" && exit 1;
            BMC_IP="$2"
            shift 2 ;;
        --u|--bmc_user)
            [ -z "$2" ] && echo "ERROR: BMC user not provided" && exit 1;
            BMC_USER="$2"
            shift 2 ;;
        --p|--bmc_pass)
            [ -z "$2" ] && echo "ERROR: BMC password not provided" && exit 1;
            BMC_PASS="$2"
            shift 2 ;;
        *)
            echo "ERROR: Unknown option provided: $1"
            exit 1 ;;
        esac
    done
}

parse_args "$@"

# Cleanup
cleanup(){
    systemctl stop rabbitmq-server
    yum remove -y consul rabbitmq-server cortx-utils
    yum remove -y cortx-sspl.noarch
}
[ "$do_cleanup" == "true" ] && cleanup

# Setup common & 3rd_party repos
echo "Setup repos" 2>&1 | tee -a ${LOG_FILE}
CORTX_MONITOR_BASE_URL="https://raw.githubusercontent.com/mariyappanp/cortx-monitor/EOS-15396_self_prv"
curl $CORTX_MONITOR_BASE_URL/low-level/files/opt/seagate/sspl/prerequisites/setup_repos.sh -o setup_repos.sh
chmod a+x setup_repos.sh

if [ "$disable_sub_mgr" == "true" ] && [ -n "$TARGET_BUILD" ]; then
    ./setup_repos.sh --disable-sub-mgr -t $TARGET_BUILD 2>&1 | tee -a ${LOG_FILE}
elif [ "$disable_sub_mgr" == "true" ]; then
    ./setup_repos.sh --disable-sub-mgr 2>&1 | tee -a ${LOG_FILE}
elif [ -n "$TARGET_BUILD" ]; then
    ./setup_repos.sh -t $TARGET_BUILD 2>&1 | tee -a ${LOG_FILE}
else
    ./setup_repos.sh 2>&1 | tee -a ${LOG_FILE}
fi
rm -rf setup_repos.sh
echo -e "\nSetup repos - Done" 2>&1 | tee -a ${LOG_FILE}


# Install prereq script dependencies
yum install -y python3
pip3 install configobj

# Install required RPMS if not available
"$install_3rd_party_packages" && {
    rpm -qa | grep "cortx-py-utils" || {
        yum install -y cortx-py-utils 2>&1 | tee -a ${LOG_FILE}
    }
    rpm -qa | grep "consul" || {
        yum install -y consul 2>&1 | tee -a ${LOG_FILE}
    }
    rpm -qa | grep "rabbitmq-server" || {
        yum install -y rabbitmq-server 2>&1 | tee -a ${LOG_FILE}
    }
}


setup_consul(){
    if ! [ -x "$(command -v consul)" ]; then
        echo "Consul is not available. \
        For consul and other 3rd party package installation, \
        check prereq script usage. Exiting."
        exit 1
    fi
    # Create config file for consul agent
    CONSUL_CONFIG_DIR='/opt/seagate/cortx/sspl/bin'
    CONSUL_CONFIG_FILE="$CONSUL_CONFIG_DIR/consul_config.json"
    if [[ ! -e "$CONSUL_CONFIG_DIR" ]]; then
        mkdir -p $(dirname "${CONSUL_CONFIG_DIR}")
    fi
    cat << EOF >> $CONSUL_CONFIG_FILE
        {
            "watches": [
                {
                    "type": "key",
                    "key": "sspl/config/SYSTEM_INFORMATION/log_level",
                    "args": ["/opt/seagate/cortx/sspl/bin/consume_cfg_change_alert"]
                }
            ]
        }
EOF
    # Invoke consul agent from fallback path
    CONSUL_PS=$(pgrep "consul" || true)
    [ -z "$CONSUL_PS" ] &&
        consul agent -dev -config-file=$CONSUL_CONFIG_FILE &>/dev/null &

    TRIES=0
    while [ -z "$CONSUL_PS" ]; do
        sleep 2
        TRIES=$((TRIES+1))
        CONSUL_PS=$(pgrep "consul" || true)
        if [ $TRIES -gt 5 ]; then
            echo "Consul service is not started"
            break
        fi
    done

    # Choose sspl.conf file based on component version
    SSPL_CONF='/etc/sspl.conf'
    curl $CORTX_MONITOR_BASE_URL/low-level/files/opt/seagate/sspl/conf/sspl.conf.${SSPL_VERSION} -o sspl.conf;
    mv sspl.conf $SSPL_CONF

    # Load sspl conf to consul
    curl $CORTX_MONITOR_BASE_URL/low-level/files/opt/seagate/sspl/prerequisites/common_config_SN.ini -o common_config_SN.ini;
    curl $CORTX_MONITOR_BASE_URL/low-level/files/opt/seagate/sspl/prerequisites/feed_sspl_conf_to_consul.py -o feed_sspl_conf_to_consul.py;
    chmod a+x feed_sspl_conf_to_consul.py

    echo "Inserting common config in consul.."
    python3 feed_sspl_conf_to_consul.py -F common_config_SN.ini -N $NODE -A $CNTRLR_A \
                    -B $CNTRLR_B -U $CNTRLR_USER -P $CNTRLR_PASS -Ap $CNTRLR_A_PORT \
                    -Bp $CNTRLR_B_PORT -bi $BMC_IP -bu $BMC_USER -bp $BMC_PASS
    rm -rf common_config_SN.ini

    # Update cluster_id in common config if not already inserted
    # TODO: Get persistent cluster_id logic
    cluster_id=$(uuidgen)
    _exists=$(consul kv get system_information/cluster_id)
    [ -z $_exists ] && consul kv put system_information/cluster_id $cluster_id

    echo "Inserting $COMPONENT config in consul.."
    python3 feed_sspl_conf_to_consul.py -F $SSPL_CONF -N $NODE -C $COMPONENT -R $RPMQ_PASS
    rm -rf feed_sspl_conf_to_consul.py
    echo "Done consul setup."
}


setup_rabbitmq(){
    curl $CORTX_MONITOR_BASE_URL/low-level/files/opt/seagate/sspl/prerequisites/sspl_rabbitmq_reinit -o sspl_rabbitmq_reinit;
    chmod a+x sspl_rabbitmq_reinit;
    python3 ./sspl_rabbitmq_reinit $SSPL_VERSION || {
        reinit_err="$?"
        echo -n "sspl_rabbitmq_reinit failed "
        echo "with exit code ${reinit_err} for product $product"
        exit 1
    }
    echo "Done rabbitmq setup."
}


# Configure consul
setup_consul 2>&1 | tee -a ${LOG_FILE}

# Configure rabbitmq-server
setup_rabbitmq 2>&1 | tee -a ${LOG_FILE}

echo "For more details see: $LOG_FILE"
echo -e "\n***** SUCCESS!!! *****" 2>&1 | tee -a ${LOG_FILE}
