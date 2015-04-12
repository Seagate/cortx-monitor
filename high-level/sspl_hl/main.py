"""
Auto-generated PLEX application.
"""
# Third party
from zope.interface import implements
from twisted.plugin import IPlugin
# PLEX
from plex.common.interfaces.iapplication import IApplication
from plex.core.plex_application import PlexApplication
from plex.servicemaker.plex_dev_app_service_maker import dev_app_run_service


class Main(PlexApplication):
    """The @string/title Application."""
    implements(IPlugin, IApplication)

main = Main("@string/title",
            "1.0",
            "@string/description",
            PlexApplication.CORE_APP)

if __name__ == "__main__":
    # Startup App Dev Mode
    dev_app_run_service()
