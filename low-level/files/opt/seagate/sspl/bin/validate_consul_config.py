import sys
import consul
import sspl_constants as sc


def validate_config():
    try:
        consul_conn = consul.Consul(host=sc.CONSUL_HOST, port=sc.CONSUL_PORT)
    except ConnectionError as conn_err:
        print("Connection error while connecting to consul :{}".format(conn_err))
        sys.exit(1)

    if consul_conn:
        try:
            product = consul_conn.kv.get(sc.SYSINFO.lower() + '/' + sc.PRODUCT)[1]["Value"].decode()
            setup = consul_conn.kv.get(sc.component + '/' + sc.SYSINFO + '/' + sc.SETUP)[1]["Value"].decode()
            is_key_invalid = False
            if setup.lower() not in [x.lower() for x in sc.setups]:
                print("Configured setup {0} not supported".format(setup))
                is_key_invalid = True
            if product.lower() not in [x.lower() for x in sc.enabled_products]:
                print("Configured product {0} not supported".format(product))
                is_key_invalid = True

            if is_key_invalid:
                sys.exit(1)
        except Exception as err:
            print("[ Error ] when validating the sspl config file in consul:{}".format(err))

if __name__ == '__main__':
    validate_config()
