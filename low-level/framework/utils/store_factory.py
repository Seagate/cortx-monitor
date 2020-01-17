from framework.utils.filestore import FileStore
from framework.utils.consulstore import ConsulStore
from framework.base.sspl_constants import StoreTypes
from framework.utils.config_reader import ConfigReader

class StorFactory:

    @staticmethod
    def get_store():

        conf_reader = ConfigReader("/etc/sspl.conf")
        store_type = conf_reader._get_value_with_default("DATASTORE",
                                                        "store_type",
                                                        StoreTypes.FILE.value)
        if store_type == StoreTypes.FILE.value:
            return FileStore()
        elif store_type == StoreTypes.CONSUL.value:
            host = conf_reader._get_value_with_default("DATASTORE",
                                                        "consul_host",
                                                        "127.0.0.1")
            port = conf_reader._get_value_with_default("DATASTORE",
                                                        "consul_port",
                                                        "8500")
            return ConsulStore(host, port)
        else:
            raise Exception("{} type store is not supported".format(store_type))

store = StorFactory.get_store()
