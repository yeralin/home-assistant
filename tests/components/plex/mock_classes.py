"""Mock classes used in tests."""
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.components.plex.const import CONF_SERVER, CONF_SERVER_IDENTIFIER

MOCK_SERVERS = [
    {
        CONF_HOST: "1.2.3.4",
        CONF_PORT: 32400,
        CONF_SERVER: "Plex Server 1",
        CONF_SERVER_IDENTIFIER: "unique_id_123",
    },
    {
        CONF_HOST: "4.3.2.1",
        CONF_PORT: 32400,
        CONF_SERVER: "Plex Server 2",
        CONF_SERVER_IDENTIFIER: "unique_id_456",
    },
]


class MockResource:
    """Mock a PlexAccount resource."""

    def __init__(self, index):
        """Initialize the object."""
        self.name = MOCK_SERVERS[index][CONF_SERVER]
        self.clientIdentifier = MOCK_SERVERS[index][  # pylint: disable=invalid-name
            CONF_SERVER_IDENTIFIER
        ]
        self.provides = ["server"]
        self._mock_plex_server = MockPlexServer(index)
        self._connections = []
        for connection in range(2):
            self._connections.append(MockConnection(connection))

    @property
    def connections(self):
        """Mock the resource connection listing method."""
        return self._connections

    def connect(self):
        """Mock the resource connect method."""
        return self._mock_plex_server


class MockConnection:  # pylint: disable=too-few-public-methods
    """Mock a single account resource connection object."""

    def __init__(self, index, ssl=True):
        """Initialize the object."""
        prefix = "https" if ssl else "http"
        self.httpuri = (
            f"http://{MOCK_SERVERS[index][CONF_HOST]}:{MOCK_SERVERS[index][CONF_PORT]}"
        )
        self.uri = f"{prefix}://{MOCK_SERVERS[index][CONF_HOST]}:{MOCK_SERVERS[index][CONF_PORT]}"
        # Only first server is local
        self.local = not bool(index)


class MockPlexAccount:
    """Mock a PlexAccount instance."""

    def __init__(self, servers=1):
        """Initialize the object."""
        self._resources = []
        for index in range(servers):
            self._resources.append(MockResource(index))

    def resource(self, name):
        """Mock the PlexAccount resource lookup method."""
        return [x for x in self._resources if x.name == name][0]

    def resources(self):
        """Mock the PlexAccount resources listing method."""
        return self._resources


class MockPlexServer:
    """Mock a PlexServer instance."""

    def __init__(self, index=0, ssl=True):
        """Initialize the object."""
        host = MOCK_SERVERS[index][CONF_HOST]
        port = MOCK_SERVERS[index][CONF_PORT]
        self.friendlyName = MOCK_SERVERS[index][  # pylint: disable=invalid-name
            CONF_SERVER
        ]
        self.machineIdentifier = MOCK_SERVERS[index][  # pylint: disable=invalid-name
            CONF_SERVER_IDENTIFIER
        ]
        prefix = "https" if ssl else "http"
        self._baseurl = f"{prefix}://{host}:{port}"

    @property
    def url_in_use(self):
        """Return URL used by PlexServer."""
        return self._baseurl
