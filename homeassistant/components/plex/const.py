"""Constants for the Plex component."""
from homeassistant.const import __version__

DOMAIN = "plex"
NAME_FORMAT = "Plex {}"

DEFAULT_PORT = 32400
DEFAULT_SSL = False
DEFAULT_VERIFY_SSL = True

PLATFORMS = ["media_player", "sensor"]
REFRESH_LISTENERS = "refresh_listeners"
SERVERS = "servers"

PLEX_CONFIG_FILE = "plex.conf"
PLEX_MEDIA_PLAYER_OPTIONS = "plex_mp_options"
PLEX_SERVER_CONFIG = "server_config"

CONF_SERVER = "server"
CONF_SERVER_IDENTIFIER = "server_id"
CONF_USE_EPISODE_ART = "use_episode_art"
CONF_SHOW_ALL_CONTROLS = "show_all_controls"

AUTH_CALLBACK_PATH = "/auth/plex/callback"
AUTH_CALLBACK_NAME = "auth:plex:callback"

X_PLEX_DEVICE_NAME = "Home Assistant"
X_PLEX_PLATFORM = "Home Assistant"
X_PLEX_PRODUCT = "Home Assistant"
X_PLEX_VERSION = __version__
