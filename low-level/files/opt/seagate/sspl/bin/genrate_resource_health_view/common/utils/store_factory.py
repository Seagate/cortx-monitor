from common.utils.filestore import FileStore
from common.utils.consulstore import ConsulStore

class StorFactory:

    @staticmethod
    def get_store():

        store_type = "file"
        if store_type == "file":
            return FileStore()
        elif store_type == "consul":
            host = "127.0.0.1"
            port = "8500"
            return ConsulStore(host, port)
        else:
            raise Exception("{} type store is not supported".format(store_type))

store = StorFactory.get_store()
