"""Google config for Cloud."""
import asyncio
import logging

import async_timeout
from hass_nabucasa.google_report_state import ErrorResponse

from homeassistant.const import CLOUD_NEVER_EXPOSED_ENTITIES
from homeassistant.components.google_assistant.helpers import AbstractConfig
from homeassistant.helpers import entity_registry

from .const import (
    PREF_SHOULD_EXPOSE,
    DEFAULT_SHOULD_EXPOSE,
    CONF_ENTITY_CONFIG,
    PREF_DISABLE_2FA,
    DEFAULT_DISABLE_2FA,
)

_LOGGER = logging.getLogger(__name__)


class CloudGoogleConfig(AbstractConfig):
    """HA Cloud Configuration for Google Assistant."""

    def __init__(self, hass, config, prefs, cloud):
        """Initialize the Google config."""
        super().__init__(hass)
        self._config = config
        self._prefs = prefs
        self._cloud = cloud
        self._cur_entity_prefs = self._prefs.google_entity_configs
        self._sync_entities_lock = asyncio.Lock()

        prefs.async_listen_updates(self._async_prefs_updated)
        hass.bus.async_listen(
            entity_registry.EVENT_ENTITY_REGISTRY_UPDATED,
            self._handle_entity_registry_updated,
        )

    @property
    def enabled(self):
        """Return if Google is enabled."""
        return self._prefs.google_enabled

    @property
    def agent_user_id(self):
        """Return Agent User Id to use for query responses."""
        return self._cloud.claims["cognito:username"]

    @property
    def entity_config(self):
        """Return entity config."""
        return self._config.get(CONF_ENTITY_CONFIG) or {}

    @property
    def secure_devices_pin(self):
        """Return entity config."""
        return self._prefs.google_secure_devices_pin

    @property
    def should_report_state(self):
        """Return if states should be proactively reported."""
        return self._prefs.google_report_state

    @property
    def local_sdk_webhook_id(self):
        """Return the local SDK webhook.

        Return None to disable the local SDK.
        """
        return self._prefs.google_local_webhook_id

    @property
    def local_sdk_user_id(self):
        """Return the user ID to be used for actions received via the local SDK."""
        return self._prefs.cloud_user

    def should_expose(self, state):
        """If a state object should be exposed."""
        return self._should_expose_entity_id(state.entity_id)

    def _should_expose_entity_id(self, entity_id):
        """If an entity ID should be exposed."""
        if entity_id in CLOUD_NEVER_EXPOSED_ENTITIES:
            return False

        if not self._config["filter"].empty_filter:
            return self._config["filter"](entity_id)

        entity_configs = self._prefs.google_entity_configs
        entity_config = entity_configs.get(entity_id, {})
        return entity_config.get(PREF_SHOULD_EXPOSE, DEFAULT_SHOULD_EXPOSE)

    def should_2fa(self, state):
        """If an entity should be checked for 2FA."""
        entity_configs = self._prefs.google_entity_configs
        entity_config = entity_configs.get(state.entity_id, {})
        return not entity_config.get(PREF_DISABLE_2FA, DEFAULT_DISABLE_2FA)

    async def async_report_state(self, message):
        """Send a state report to Google."""
        try:
            await self._cloud.google_report_state.async_send_message(message)
        except ErrorResponse as err:
            _LOGGER.warning("Error reporting state - %s: %s", err.code, err.message)

    async def _async_request_sync_devices(self):
        """Trigger a sync with Google."""
        if self._sync_entities_lock.locked():
            return 200

        websession = self.hass.helpers.aiohttp_client.async_get_clientsession()

        async with self._sync_entities_lock:
            with async_timeout.timeout(10):
                await self._cloud.auth.async_check_token()

            _LOGGER.debug("Requesting sync")

            with async_timeout.timeout(30):
                req = await websession.post(
                    self._cloud.google_actions_sync_url,
                    headers={"authorization": self._cloud.id_token},
                )
                _LOGGER.debug("Finished requesting syncing: %s", req.status)
                return req.status

    async def async_deactivate_report_state(self):
        """Turn off report state and disable further state reporting.

        Called when the user disconnects their account from Google.
        """
        await self._prefs.async_update(google_report_state=False)

    async def _async_prefs_updated(self, prefs):
        """Handle updated preferences."""
        if self.should_report_state != self.is_reporting_state:
            if self.should_report_state:
                self.async_enable_report_state()
            else:
                self.async_disable_report_state()

            # State reporting is reported as a property on entities.
            # So when we change it, we need to sync all entities.
            await self.async_sync_entities()

        # If entity prefs are the same or we have filter in config.yaml,
        # don't sync.
        elif (
            self._cur_entity_prefs is not prefs.google_entity_configs
            and self._config["filter"].empty_filter
        ):
            self.async_schedule_google_sync()

        if self.enabled and not self.is_local_sdk_active:
            self.async_enable_local_sdk()
        elif not self.enabled and self.is_local_sdk_active:
            self.async_disable_local_sdk()

    async def _handle_entity_registry_updated(self, event):
        """Handle when entity registry updated."""
        if not self.enabled or not self._cloud.is_logged_in:
            return

        entity_id = event.data["entity_id"]

        # Schedule a sync if a change was made to an entity that Google knows about
        if self._should_expose_entity_id(entity_id):
            await self.async_sync_entities()
