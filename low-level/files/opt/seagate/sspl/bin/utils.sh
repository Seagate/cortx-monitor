# Contains common functions

script_dir=$(dirname $0)

# Import common constants
source $script_dir/constants.sh

get_amqp_type(){
    echo $($CONSUL_PATH/consul kv get sspl/config/AMQP/type)
}

validate_amqp_type(){
    amqp_type=$1
    if ! [[ $AMQP_TYPES =~ (^| )$amqp_type($| ) ]]
    then
        echo "Message broker type $amqp_type is not supported"
        exit 1;
    fi
}

