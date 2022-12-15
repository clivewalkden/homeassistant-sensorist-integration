import aiohttp
import logging

_LOGGER = logging.getLogger(__name__)


class SensoristApi:
    """Interact with the Sensorist API with this class"""

    def __init__(self, username: str, password: str) -> None:
        """Class setup with basic requirements to connect"""
        auth = None
        if username != None and password != None:
            auth = aiohttp.BasicAuth(
                login=username, password=password, encoding="utf-8"
            )
        self.host = "https://api.sensorist.com/v1"

        self.headers = {"Content-Type": "application/json"}
        self.session = aiohttp.ClientSession(headers=self.headers, auth=auth)
        self.data = None
        self.gateways = None
        self.devices = None
        self.sensors = None
        _LOGGER.debug("Sensorist API __init__")

    async def test(self):
        """Test the integration can access the api"""
        _LOGGER.debug("Sensorist API test")
        try:
            resp = await self.users()
        except aiohttp.client_exceptions.ClientResponseError as err:
            _LOGGER.debug(
                "A aiohttp.client_exceptions.ClientResponseError thrown in test() %s",
                err.message,
            )
            return False

        return resp

    async def users(self):
        """Get the user information for the username and passsord supplied"""
        _LOGGER.debug("Sensorist API users")
        url = f"{self.host}/users"
        try:
            resp = await self.make_request(url)
            _LOGGER.debug(resp)
            return resp
        except aiohttp.client_exceptions.ClientResponseError as err:
            _LOGGER.debug(
                "A aiohttp.client_exceptions.ClientResponseError thrown in users() %s",
                err.message,
            )
            return False

    async def list_devices(self):
        """Retrieve all account device information"""
        _LOGGER.debug("Call to all devices()")
        url = f"{self.host}/gateways"
        try:
            resp = await self.make_request(url)
            _LOGGER.debug(resp)
            return resp
        except aiohttp.client_exceptions.ClientResponseError as err:
            _LOGGER.debug(
                "A aiohttp.client_exceptions.ClientResponseError thrown in list_devices() %s",
                err.message,
            )
            return False

    async def get_sensor_data(self, sensor_id):
        """Retrieve a Sensors current data"""
        url = f"{self.host}/measurements?data_sources={sensor_id}&type=latest"
        try:
            resp = await self.make_request(url)
            _LOGGER.debug(resp)
            return resp
        except aiohttp.client_exceptions.ClientResponseError as err:
            _LOGGER.debug(
                "A aiohttp.client_exceptions.ClientResponseError thrown in get_sensor_data() %s",
                err.message,
            )
            return False

    async def make_request(self, url):
        """Make a request to the Sensorist API"""
        _LOGGER.debug("Sensorist API make_request")

        async with self.session.get(url) as resp:
            resp.raise_for_status()
            self.data = await resp.json()
            return self.data
