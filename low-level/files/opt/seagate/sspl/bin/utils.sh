# Contains common functions

script_dir=$(dirname $0)

# Import common constants
source $script_dir/constants.sh

get_messaging_bus_type(){
    echo $($CONSUL_PATH/consul kv get sspl/config/MESSAGING/type)
}

validate_messaging_bus_type(){
    messaging_bus_type=$1
    if ! [[ $MESSAGING_BUS_TYPES =~ (^| )$messaging_bus_type($| ) ]]
    then
        echo "Message broker type $messaging_bus_type is not supported"
        exit 1;
    fi
}

