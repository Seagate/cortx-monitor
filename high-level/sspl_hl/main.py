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


class Main(PlexApplication):  # pylint: disable=too-many-public-methods
    """The @string/title Application."""
    implements(IPlugin, IApplication)


# pylint: disable=invalid-name
main = Main("@string/title",
            "1.0",
            "@string/description",
            PlexApplication.CORE_APP)
# pylint: enable=invalid-name

if __name__ == "__main__":
    # Startup App Dev Mode
    dev_app_run_service()
