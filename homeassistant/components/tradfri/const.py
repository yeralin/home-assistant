"""Consts used by Tradfri."""
from homeassistant.components.light import SUPPORT_TRANSITION, SUPPORT_BRIGHTNESS
from homeassistant.const import CONF_HOST  # noqa pylint: disable=unused-import

ATTR_DIMMER = "dimmer"
ATTR_HUE = "hue"
ATTR_SAT = "saturation"
ATTR_TRADFRI_GATEWAY = "Gateway"
ATTR_TRADFRI_GATEWAY_MODEL = "E1526"
ATTR_TRADFRI_MANUFACTURER = "IKEA"
ATTR_TRANSITION_TIME = "transition_time"
CONF_ALLOW_TRADFRI_GROUPS = "allow_tradfri_groups"
CONF_IDENTITY = "identity"
CONF_IMPORT_GROUPS = "import_groups"
CONF_GATEWAY_ID = "gateway_id"
CONF_KEY = "key"
CONFIG_FILE = ".tradfri_psk.conf"
DEFAULT_ALLOW_TRADFRI_GROUPS = False
DOMAIN = "tradfri"
KEY_API = "tradfri_api"
KEY_GATEWAY = "tradfri_gateway"
KEY_SECURITY_CODE = "security_code"
SUPPORTED_GROUP_FEATURES = SUPPORT_BRIGHTNESS | SUPPORT_TRANSITION
SUPPORTED_LIGHT_FEATURES = SUPPORT_TRANSITION
TRADFRI_DEVICE_TYPES = ["cover", "light", "sensor", "switch"]
