# This script contains common constants used by various provisioner scripts

PRODUCT_NAME='ECS'
PRODUCT_FAMILY='eos'
PRODUCTS="SINGLE EES ECS"
SSPL_CONF="/etc/sspl.conf"
ROLES="gw ssu vm cmu eos"
PRODUCT_BASE_DIR="/opt/seagate/$PRODUCT_FAMILY/"
SSPL_BASE_DIR="/opt/seagate/$PRODUCT_FAMILY/sspl"
SSPL_STORE_TYPE="consul"
CONSUL_HOST="127.0.0.1"
CONSUL_PORT="8500"
ENVIRONMENT="PROD"
CONSUL_PATH="/opt/seagate/$PRODUCT_FAMILY/hare/bin"
CONSUL_FALLBACK_PATH="/opt/seagate/$PRODUCT_FAMILY/sspl/bin"
