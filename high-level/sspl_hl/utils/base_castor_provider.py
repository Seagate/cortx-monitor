""" uitls
"""
from plex.util.concurrent.single_thread_executor import SingleThreadExecutor
from plex.common.interfaces.idata_provider import IDataProvider
from twisted.plugin import IPlugin
from plex.core.provider.data_store_provider import DataStoreProvider
from zope.interface import implements


class BaseCastorProvider(DataStoreProvider):
    # pylint: disable=too-many-ancestors,too-many-public-methods

    """ Used to set state of ha on the cluster. """
    implements(IPlugin, IDataProvider)

    def __init__(self, name, description):
        super(BaseCastorProvider, self).__init__(name, description)
        self._single_thread_executor = SingleThreadExecutor()

    def query(
            self, uri, columns, selection_args, sort_order,
            range_from, range_to, responder
    ):  # pylint: disable=too-many-arguments
        self._single_thread_executor.submit(
            self._query, selection_args, responder
        )

    def _query(self, selection_args, responder):
        pass
