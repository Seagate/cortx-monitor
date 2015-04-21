"""
PLEX data provider.
"""
# Third party
from zope.interface import implements
from twisted.plugin import IPlugin
# PLEX
from plex.common.interfaces.idata_provider import IDataProvider
from plex.core.provider.data_store_provider import DataStoreProvider
# Local


class Provider(DataStoreProvider):
    """Data Provider"""
    implements(IPlugin, IDataProvider)

    def on_create(self):
        """Implement this method to initialize the Provider."""
        pass

provider = Provider("service",
                    "The Hello Data Provider")
