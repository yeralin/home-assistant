"""Support to interface with the Plex API."""
from datetime import timedelta
import json
import logging
from xml.etree.ElementTree import ParseError

import plexapi.exceptions
import requests.exceptions

from homeassistant.components.media_player import MediaPlayerDevice
from homeassistant.components.media_player.const import (
    MEDIA_TYPE_MOVIE,
    MEDIA_TYPE_MUSIC,
    MEDIA_TYPE_TVSHOW,
    SUPPORT_NEXT_TRACK,
    SUPPORT_PAUSE,
    SUPPORT_PLAY,
    SUPPORT_PLAY_MEDIA,
    SUPPORT_PREVIOUS_TRACK,
    SUPPORT_STOP,
    SUPPORT_TURN_OFF,
    SUPPORT_VOLUME_MUTE,
    SUPPORT_VOLUME_SET,
)
from homeassistant.const import (
    DEVICE_DEFAULT_NAME,
    STATE_IDLE,
    STATE_OFF,
    STATE_PAUSED,
    STATE_PLAYING,
)
from homeassistant.helpers.event import track_time_interval
from homeassistant.util import dt as dt_util

from .const import (
    CONF_SERVER_IDENTIFIER,
    DOMAIN as PLEX_DOMAIN,
    NAME_FORMAT,
    REFRESH_LISTENERS,
    SERVERS,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the Plex media_player platform.

    Deprecated.
    """
    pass


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up Plex media_player from a config entry."""

    def add_entities(entities, update_before_add=False):
        """Sync version of async add entities."""
        hass.add_job(async_add_entities, entities, update_before_add)

    hass.async_add_executor_job(_setup_platform, hass, config_entry, add_entities)


def _setup_platform(hass, config_entry, add_entities_callback):
    """Set up the Plex media_player platform."""
    server_id = config_entry.data[CONF_SERVER_IDENTIFIER]
    plexserver = hass.data[PLEX_DOMAIN][SERVERS][server_id]
    plex_clients = {}
    plex_sessions = {}
    hass.data[PLEX_DOMAIN][REFRESH_LISTENERS][server_id] = track_time_interval(
        hass, lambda now: update_devices(), timedelta(seconds=10)
    )

    def update_devices():
        """Update the devices objects."""
        try:
            devices = plexserver.clients()
        except plexapi.exceptions.BadRequest:
            _LOGGER.exception("Error listing plex devices")
            return
        except requests.exceptions.RequestException as ex:
            _LOGGER.warning(
                "Could not connect to Plex server: %s (%s)",
                plexserver.friendly_name,
                ex,
            )
            return

        new_plex_clients = []
        available_client_ids = []
        for device in devices:
            # For now, let's allow all deviceClass types
            if device.deviceClass in ["badClient"]:
                continue

            available_client_ids.append(device.machineIdentifier)

            if device.machineIdentifier not in plex_clients:
                new_client = PlexClient(
                    plexserver, device, None, plex_sessions, update_devices
                )
                plex_clients[device.machineIdentifier] = new_client
                _LOGGER.debug("New device: %s", device.machineIdentifier)
                new_plex_clients.append(new_client)
            else:
                _LOGGER.debug("Refreshing device: %s", device.machineIdentifier)
                plex_clients[device.machineIdentifier].refresh(device, None)

        # add devices with a session and no client (ex. PlexConnect Apple TV's)
        try:
            sessions = plexserver.sessions()
        except plexapi.exceptions.BadRequest:
            _LOGGER.exception("Error listing plex sessions")
            return
        except requests.exceptions.RequestException as ex:
            _LOGGER.warning(
                "Could not connect to Plex server: %s (%s)",
                plexserver.friendly_name,
                ex,
            )
            return

        plex_sessions.clear()
        for session in sessions:
            for player in session.players:
                plex_sessions[player.machineIdentifier] = session, player

        for machine_identifier, (session, player) in plex_sessions.items():
            if machine_identifier in available_client_ids:
                # Avoid using session if already added as a device.
                _LOGGER.debug("Skipping session, device exists: %s", machine_identifier)
                continue

            if (
                machine_identifier not in plex_clients
                and machine_identifier is not None
            ):
                new_client = PlexClient(
                    plexserver, player, session, plex_sessions, update_devices
                )
                plex_clients[machine_identifier] = new_client
                _LOGGER.debug("New session: %s", machine_identifier)
                new_plex_clients.append(new_client)
            else:
                _LOGGER.debug("Refreshing session: %s", machine_identifier)
                plex_clients[machine_identifier].refresh(None, session)

        for client in plex_clients.values():
            # force devices to idle that do not have a valid session
            if client.session is None:
                client.force_idle()

            client.set_availability(
                client.machine_identifier in available_client_ids
                or client.machine_identifier in plex_sessions
            )

            if client not in new_plex_clients:
                client.schedule_update_ha_state()

        if new_plex_clients:
            add_entities_callback(new_plex_clients)


class PlexClient(MediaPlayerDevice):
    """Representation of a Plex device."""

    def __init__(self, plex_server, device, session, plex_sessions, update_devices):
        """Initialize the Plex device."""
        self._app_name = ""
        self._device = None
        self._available = False
        self._marked_unavailable = None
        self._device_protocol_capabilities = None
        self._is_player_active = False
        self._is_player_available = False
        self._player = None
        self._machine_identifier = None
        self._make = ""
        self._name = None
        self._player_state = "idle"
        self._previous_volume_level = 1  # Used in fake muting
        self._session = None
        self._session_type = None
        self._session_username = None
        self._state = STATE_IDLE
        self._volume_level = 1  # since we can't retrieve remotely
        self._volume_muted = False  # since we can't retrieve remotely
        self.plex_server = plex_server
        self.plex_sessions = plex_sessions
        self.update_devices = update_devices
        # General
        self._media_content_id = None
        self._media_content_rating = None
        self._media_content_type = None
        self._media_duration = None
        self._media_image_url = None
        self._media_title = None
        self._media_position = None
        self._media_position_updated_at = None
        # Music
        self._media_album_artist = None
        self._media_album_name = None
        self._media_artist = None
        self._media_track = None
        # TV Show
        self._media_episode = None
        self._media_season = None
        self._media_series_title = None

        self.refresh(device, session)

    def _clear_media_details(self):
        """Set all Media Items to None."""
        # General
        self._media_content_id = None
        self._media_content_rating = None
        self._media_content_type = None
        self._media_duration = None
        self._media_image_url = None
        self._media_title = None
        # Music
        self._media_album_artist = None
        self._media_album_name = None
        self._media_artist = None
        self._media_track = None
        # TV Show
        self._media_episode = None
        self._media_season = None
        self._media_series_title = None

        # Clear library Name
        self._app_name = ""

    def refresh(self, device, session):
        """Refresh key device data."""
        self._clear_media_details()

        if session:  # Not being triggered by Chrome or FireTablet Plex App
            self._session = session
        if device:
            self._device = device
            try:
                device_url = self._device.url("/")
            except plexapi.exceptions.BadRequest:
                device_url = "127.0.0.1"
            if "127.0.0.1" in device_url:
                self._device.proxyThroughServer()
            self._session = None
            self._machine_identifier = self._device.machineIdentifier
            self._name = NAME_FORMAT.format(self._device.title or DEVICE_DEFAULT_NAME)
            self._device_protocol_capabilities = self._device.protocolCapabilities

            # set valid session, preferring device session
            if self._device.machineIdentifier in self.plex_sessions:
                self._session = self.plex_sessions.get(
                    self._device.machineIdentifier, [None, None]
                )[0]

        if self._session:
            if (
                self._device is not None
                and self._device.machineIdentifier is not None
                and self._session.players
            ):
                self._is_player_available = True
                self._player = [
                    p
                    for p in self._session.players
                    if p.machineIdentifier == self._device.machineIdentifier
                ][0]
                self._name = NAME_FORMAT.format(self._player.title)
                self._player_state = self._player.state
                self._session_username = self._session.usernames[0]
                self._make = self._player.device
            else:
                self._is_player_available = False

            # Calculate throttled position for proper progress display.
            position = int(self._session.viewOffset / 1000)
            now = dt_util.utcnow()
            if self._media_position is not None:
                pos_diff = position - self._media_position
                time_diff = now - self._media_position_updated_at
                if pos_diff != 0 and abs(time_diff.total_seconds() - pos_diff) > 5:
                    self._media_position_updated_at = now
                    self._media_position = position
            else:
                self._media_position_updated_at = now
                self._media_position = position

            self._media_content_id = self._session.ratingKey
            self._media_content_rating = getattr(self._session, "contentRating", None)

        self._set_player_state()

        if self._is_player_active and self._session is not None:
            self._session_type = self._session.type
            self._media_duration = int(self._session.duration / 1000)
            #  title (movie name, tv episode name, music song name)
            self._media_title = self._session.title
            # media type
            self._set_media_type()
            self._app_name = (
                self._session.section().title
                if self._session.section() is not None
                else ""
            )
            self._set_media_image()
        else:
            self._session_type = None

    def _set_media_image(self):
        thumb_url = self._session.thumbUrl
        if (
            self.media_content_type is MEDIA_TYPE_TVSHOW
            and not self.plex_server.use_episode_art
        ):
            thumb_url = self._session.url(self._session.grandparentThumb)

        if thumb_url is None:
            _LOGGER.debug(
                "Using media art because media thumb " "was not found: %s",
                self.entity_id,
            )
            thumb_url = self.session.url(self._session.art)

        self._media_image_url = thumb_url

    def set_availability(self, available):
        """Set the device as available/unavailable noting time."""
        if not available:
            self._clear_media_details()
            if self._marked_unavailable is None:
                self._marked_unavailable = dt_util.utcnow()
        else:
            self._marked_unavailable = None

        self._available = available

    def _set_player_state(self):
        if self._player_state == "playing":
            self._is_player_active = True
            self._state = STATE_PLAYING
        elif self._player_state == "paused":
            self._is_player_active = True
            self._state = STATE_PAUSED
        elif self.device:
            self._is_player_active = False
            self._state = STATE_IDLE
        else:
            self._is_player_active = False
            self._state = STATE_OFF

    def _set_media_type(self):
        if self._session_type in ["clip", "episode"]:
            self._media_content_type = MEDIA_TYPE_TVSHOW

            # season number (00)
            if callable(self._session.season):
                self._media_season = str((self._session.season()).index).zfill(2)
            elif self._session.parentIndex is not None:
                self._media_season = self._session.parentIndex.zfill(2)
            else:
                self._media_season = None
            # show name
            self._media_series_title = self._session.grandparentTitle
            # episode number (00)
            if self._session.index is not None:
                self._media_episode = str(self._session.index).zfill(2)

        elif self._session_type == "movie":
            self._media_content_type = MEDIA_TYPE_MOVIE
            if self._session.year is not None and self._media_title is not None:
                self._media_title += " (" + str(self._session.year) + ")"

        elif self._session_type == "track":
            self._media_content_type = MEDIA_TYPE_MUSIC
            self._media_album_name = self._session.parentTitle
            self._media_album_artist = self._session.grandparentTitle
            self._media_track = self._session.index
            self._media_artist = self._session.originalTitle
            # use album artist if track artist is missing
            if self._media_artist is None:
                _LOGGER.debug(
                    "Using album artist because track artist " "was not found: %s",
                    self.entity_id,
                )
                self._media_artist = self._media_album_artist

    def force_idle(self):
        """Force client to idle."""
        self._state = STATE_IDLE
        self._session = None
        self._clear_media_details()

    @property
    def should_poll(self):
        """Return True if entity has to be polled for state."""
        return False

    @property
    def unique_id(self):
        """Return the id of this plex client."""
        return self.machine_identifier

    @property
    def available(self):
        """Return the availability of the client."""
        return self._available

    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    @property
    def machine_identifier(self):
        """Return the machine identifier of the device."""
        return self._machine_identifier

    @property
    def app_name(self):
        """Return the library name of playing media."""
        return self._app_name

    @property
    def device(self):
        """Return the device, if any."""
        return self._device

    @property
    def marked_unavailable(self):
        """Return time device was marked unavailable."""
        return self._marked_unavailable

    @property
    def session(self):
        """Return the session, if any."""
        return self._session

    @property
    def state(self):
        """Return the state of the device."""
        return self._state

    @property
    def _active_media_plexapi_type(self):
        """Get the active media type required by PlexAPI commands."""
        if self.media_content_type is MEDIA_TYPE_MUSIC:
            return "music"

        return "video"

    @property
    def media_content_id(self):
        """Return the content ID of current playing media."""
        return self._media_content_id

    @property
    def media_content_type(self):
        """Return the content type of current playing media."""
        if self._session_type == "clip":
            _LOGGER.debug(
                "Clip content type detected, " "compatibility may vary: %s",
                self.entity_id,
            )
            return MEDIA_TYPE_TVSHOW
        if self._session_type == "episode":
            return MEDIA_TYPE_TVSHOW
        if self._session_type == "movie":
            return MEDIA_TYPE_MOVIE
        if self._session_type == "track":
            return MEDIA_TYPE_MUSIC

        return None

    @property
    def media_artist(self):
        """Return the artist of current playing media, music track only."""
        return self._media_artist

    @property
    def media_album_name(self):
        """Return the album name of current playing media, music track only."""
        return self._media_album_name

    @property
    def media_album_artist(self):
        """Return the album artist of current playing media, music only."""
        return self._media_album_artist

    @property
    def media_track(self):
        """Return the track number of current playing media, music only."""
        return self._media_track

    @property
    def media_duration(self):
        """Return the duration of current playing media in seconds."""
        return self._media_duration

    @property
    def media_position(self):
        """Return the duration of current playing media in seconds."""
        return self._media_position

    @property
    def media_position_updated_at(self):
        """When was the position of the current playing media valid."""
        return self._media_position_updated_at

    @property
    def media_image_url(self):
        """Return the image URL of current playing media."""
        return self._media_image_url

    @property
    def media_title(self):
        """Return the title of current playing media."""
        return self._media_title

    @property
    def media_season(self):
        """Return the season of current playing media (TV Show only)."""
        return self._media_season

    @property
    def media_series_title(self):
        """Return the title of the series of current playing media."""
        return self._media_series_title

    @property
    def media_episode(self):
        """Return the episode of current playing media (TV Show only)."""
        return self._media_episode

    @property
    def make(self):
        """Return the make of the device (ex. SHIELD Android TV)."""
        return self._make

    @property
    def supported_features(self):
        """Flag media player features that are supported."""
        # force show all controls
        if self.plex_server.show_all_controls:
            return (
                SUPPORT_PAUSE
                | SUPPORT_PREVIOUS_TRACK
                | SUPPORT_NEXT_TRACK
                | SUPPORT_STOP
                | SUPPORT_VOLUME_SET
                | SUPPORT_PLAY
                | SUPPORT_PLAY_MEDIA
                | SUPPORT_TURN_OFF
                | SUPPORT_VOLUME_MUTE
            )

        # no mute support
        if self.make.lower() == "shield android tv":
            _LOGGER.debug(
                "Shield Android TV client detected, disabling mute " "controls: %s",
                self.entity_id,
            )
            return (
                SUPPORT_PAUSE
                | SUPPORT_PREVIOUS_TRACK
                | SUPPORT_NEXT_TRACK
                | SUPPORT_STOP
                | SUPPORT_VOLUME_SET
                | SUPPORT_PLAY
                | SUPPORT_PLAY_MEDIA
                | SUPPORT_TURN_OFF
            )

        # Only supports play,pause,stop (and off which really is stop)
        if self.make.lower().startswith("tivo"):
            _LOGGER.debug(
                "Tivo client detected, only enabling pause, play, "
                "stop, and off controls: %s",
                self.entity_id,
            )
            return SUPPORT_PAUSE | SUPPORT_PLAY | SUPPORT_STOP | SUPPORT_TURN_OFF

        if self.device and "playback" in self._device_protocol_capabilities:
            return (
                SUPPORT_PAUSE
                | SUPPORT_PREVIOUS_TRACK
                | SUPPORT_NEXT_TRACK
                | SUPPORT_STOP
                | SUPPORT_VOLUME_SET
                | SUPPORT_PLAY
                | SUPPORT_PLAY_MEDIA
                | SUPPORT_TURN_OFF
                | SUPPORT_VOLUME_MUTE
            )

        return 0

    def set_volume_level(self, volume):
        """Set volume level, range 0..1."""
        if self.device and "playback" in self._device_protocol_capabilities:
            self.device.setVolume(int(volume * 100), self._active_media_plexapi_type)
            self._volume_level = volume  # store since we can't retrieve
            self.update_devices()

    @property
    def volume_level(self):
        """Return the volume level of the client (0..1)."""
        if (
            self._is_player_active
            and self.device
            and "playback" in self._device_protocol_capabilities
        ):
            return self._volume_level

    @property
    def is_volume_muted(self):
        """Return boolean if volume is currently muted."""
        if self._is_player_active and self.device:
            return self._volume_muted

    def mute_volume(self, mute):
        """Mute the volume.

        Since we can't actually mute, we'll:
        - On mute, store volume and set volume to 0
        - On unmute, set volume to previously stored volume
        """
        if not (self.device and "playback" in self._device_protocol_capabilities):
            return

        self._volume_muted = mute
        if mute:
            self._previous_volume_level = self._volume_level
            self.set_volume_level(0)
        else:
            self.set_volume_level(self._previous_volume_level)

    def media_play(self):
        """Send play command."""
        if self.device and "playback" in self._device_protocol_capabilities:
            self.device.play(self._active_media_plexapi_type)
            self.update_devices()

    def media_pause(self):
        """Send pause command."""
        if self.device and "playback" in self._device_protocol_capabilities:
            self.device.pause(self._active_media_plexapi_type)
            self.update_devices()

    def media_stop(self):
        """Send stop command."""
        if self.device and "playback" in self._device_protocol_capabilities:
            self.device.stop(self._active_media_plexapi_type)
            self.update_devices()

    def turn_off(self):
        """Turn the client off."""
        # Fake it since we can't turn the client off
        self.media_stop()

    def media_next_track(self):
        """Send next track command."""
        if self.device and "playback" in self._device_protocol_capabilities:
            self.device.skipNext(self._active_media_plexapi_type)
            self.update_devices()

    def media_previous_track(self):
        """Send previous track command."""
        if self.device and "playback" in self._device_protocol_capabilities:
            self.device.skipPrevious(self._active_media_plexapi_type)
            self.update_devices()

    def play_media(self, media_type, media_id, **kwargs):
        """Play a piece of media."""
        if not (self.device and "playback" in self._device_protocol_capabilities):
            return

        src = json.loads(media_id)
        library = src.get("library_name")
        shuffle = src.get("shuffle", 0)

        media = None

        if media_type == "MUSIC":
            media = self._get_music_media(library, src)
        elif media_type == "EPISODE":
            media = self._get_tv_media(library, src)
        elif media_type == "PLAYLIST":
            media = self.plex_server.playlist(src["playlist_name"])
        elif media_type == "VIDEO":
            media = self.plex_server.library.section(library).get(src["video_name"])

        if media is None:
            _LOGGER.error("Media could not be found: %s", media_id)
            return

        playqueue = self.plex_server.create_playqueue(media, shuffle=shuffle)
        try:
            self.device.playMedia(playqueue)
        except ParseError:
            # Temporary workaround for Plexamp / plexapi issue
            pass
        except requests.exceptions.ConnectTimeout:
            _LOGGER.error("Timed out playing on %s", self.name)

        self.update_devices()

    def _get_music_media(self, library_name, src):
        """Find music media and return a Plex media object."""
        artist_name = src["artist_name"]
        album_name = src.get("album_name")
        track_name = src.get("track_name")
        track_number = src.get("track_number")

        artist = self.plex_server.library.section(library_name).get(artist_name)

        if album_name:
            album = artist.album(album_name)

            if track_name:
                return album.track(track_name)

            if track_number:
                for track in album.tracks():
                    if int(track.index) == int(track_number):
                        return track
                return None

            return album

        if track_name:
            return artist.searchTracks(track_name, maxresults=1)
        return artist

    def _get_tv_media(self, library_name, src):
        """Find TV media and return a Plex media object."""
        show_name = src["show_name"]
        season_number = src.get("season_number")
        episode_number = src.get("episode_number")
        target_season = None
        target_episode = None

        show = self.plex_server.library.section(library_name).get(show_name)

        if not season_number:
            return show

        for season in show.seasons():
            if int(season.seasonNumber) == int(season_number):
                target_season = season
                break

        if target_season is None:
            _LOGGER.error(
                "Season not found: %s\\%s - S%sE%s",
                library_name,
                show_name,
                str(season_number).zfill(2),
                str(episode_number).zfill(2),
            )
        else:
            if not episode_number:
                return target_season

            for episode in target_season.episodes():
                if int(episode.index) == int(episode_number):
                    target_episode = episode
                    break

            if target_episode is None:
                _LOGGER.error(
                    "Episode not found: %s\\%s - S%sE%s",
                    library_name,
                    show_name,
                    str(season_number).zfill(2),
                    str(episode_number).zfill(2),
                )

        return target_episode

    @property
    def device_state_attributes(self):
        """Return the scene state attributes."""
        attr = {
            "media_content_rating": self._media_content_rating,
            "session_username": self._session_username,
            "media_library_name": self._app_name,
        }

        return attr
