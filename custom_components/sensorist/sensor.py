import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import TEMP_CELSIUS, ELECTRIC_POTENTIAL_VOLT, PERCENTAGE
from homeassistant.components.sensor import (
    RestoreSensor,
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from datetime import timedelta

from .api import SensoristApi
from .const import DOMAIN, DEVICE_MANUFACTURER, DEVICE_CONFIGURATION_URL

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(minutes=15)


SENSORS_MAP = {
    "batt": {
        "name": "Battery",
        "native_unit_of_measurement": ELECTRIC_POTENTIAL_VOLT,
        "device_class": SensorDeviceClass.VOLTAGE,
        "state_class": SensorStateClass.MEASUREMENT,
        "icon": "mdi:battery",
    },
    "wireless": {
        "name": "Signal Strength",
        "native_unit_of_measurement": PERCENTAGE,
        "device_class": SensorDeviceClass.POWER_FACTOR,
        "state_class": SensorStateClass.MEASUREMENT,
        "icon": "mdi:wifi",
    },
    "temp": {
        "name": "Temperature",
        "native_unit_of_measurement": TEMP_CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
        "icon": "mdi:thermometer",
    },
    "humi": {
        "name": "Humidity",
        "native_unit_of_measurement": PERCENTAGE,
        "device_class": SensorDeviceClass.HUMIDITY,
        "state_class": SensorStateClass.MEASUREMENT,
        "icon": "mdi:water-percent",
    },
}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Sensorist sensor Platform"""
    _LOGGER.info(hass.data[DOMAIN])
    config = hass.data[DOMAIN][config_entry.entry_id]
    api = config["api"]
    entities = []
    _LOGGER.info(hass.data[DOMAIN]["known_probes"])
    known_probes: set = hass.data[DOMAIN]["known_probes"]

    devices = await api.list_devices()
    for gateway in devices["gateways"]:
        if gateway["id"] not in known_probes:
            gateway_device = SensoristHub(gateway)
            entities.append(gateway_device)
            known_probes.add(gateway["id"])

        # Get the individual sensor devices
        for device in gateway["devices"]:
            if device["id"] not in known_probes:
                device_sensor = SensoristDevice(device, gateway_device)
                # entities.append(device_sensor) # Don't register the device itself
                known_probes.add(device["id"])

            for sensor in device["devices"]:
                if sensor["id"] in known_probes:
                    continue
                entities.append(
                    SensoristSensor(sensor, device_sensor, gateway_device, api)
                )
                known_probes.add(sensor["id"])

                _LOGGER.info(sensor)

    _LOGGER.info(hass.data[DOMAIN]["known_probes"])
    _LOGGER.info(entities)

    async_add_entities(entities)


class SensoristHub(Entity):
    """Representation of the Hub"""

    def __init__(self, data) -> None:
        self.data = data

    @property
    def name(self) -> str:
        """Return the name of the device"""
        return f"Sensorist Gateway {self.data['title']}"

    @property
    def unique_id(self) -> str:
        """Return the unique_id as the serial number"""
        return self.data["serial"]

    @property
    def sw_version(self):
        """Return the firmware version"""
        return self.data["firmware"]

    @property
    def model(self):
        """Return the model number"""
        return self.data["type"]["name"]

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""

        return DeviceInfo(
            identifiers={
                # Serial numbers are unique identifiers within a specific domain
                (DOMAIN, self.unique_id)
            },
            name=self.name,
            manufacturer=DEVICE_MANUFACTURER,
            configuration_url=DEVICE_CONFIGURATION_URL,
            model=f"Gateway {self.model}",
            sw_version=self.sw_version,
        )


class SensoristDevice(Entity):
    """Representation of the Device"""

    def __init__(self, data, gateway: SensoristHub) -> None:
        self.data = data
        self.gateway = gateway

    @property
    def name(self) -> str:
        """Return the name of the device"""
        return f"Sensor {self.data['title']}"

    @property
    def unique_id(self) -> str:
        """Return the unique_id as the serial number"""
        return self.data["serial"]

    @property
    def sw_version(self):
        """Return the firmware version"""
        return self.data["firmware"]

    @property
    def model(self):
        """Return the model number"""
        return self.data["type"]["name"]

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""

        return DeviceInfo(
            identifiers={
                # Serial numbers are unique identifiers within a specific domain
                (DOMAIN, self.unique_id)
            },
            name=self.name,
            manufacturer=DEVICE_MANUFACTURER,
            configuration_url=DEVICE_CONFIGURATION_URL,
            model=f"Sensor {self.model}",
            sw_version=self.sw_version,
            via_device=(DOMAIN, self.gateway.unique_id),
        )


class SensoristSensor(RestoreSensor, SensorEntity):
    """Representation of the Sensor"""

    _attr_has_entity_name = True

    def __init__(
        self, data, device: SensoristDevice, gateway: SensoristHub, api: SensoristApi
    ) -> None:
        """Initialize the SensoristSensor"""
        self.data = data
        self.device = device
        self.gateway = gateway
        self.api = api
        self.sensor = data["type"]["name"]

    @property
    def name(self):
        """Return the Sensor name"""
        # if self.data["type"]["name"] == "batt":
        #    return None
        # else:
        # return f"{self.device.name} {self.data['title']}"
        return SENSORS_MAP[self.sensor]["name"]

    @property
    def state_class(self):
        """Return the state class of this entity, if any."""
        return SENSORS_MAP[self.sensor]["state_class"]

    @property
    def device_class(self) -> SensorDeviceClass:
        """Return the class of this entity."""
        return SENSORS_MAP[self.sensor]["device_class"]

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the unit of measurement of the sensor, if any."""
        return SENSORS_MAP[self.sensor]["native_unit_of_measurement"]

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return f"sensorist.{self.device.unique_id}_{self.data['title'].lower}"

    @property
    def icon(self):
        return SENSORS_MAP[self.sensor]["icon"]

    @property
    def api_id(self) -> int:
        """Store the sensor api id for polling"""
        return self.data["id"]

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""

        return DeviceInfo(
            identifiers={
                # Serial numbers are unique identifiers within a specific domain
                (DOMAIN, self.device.unique_id)
            },
            name=self.device.name,
            manufacturer=DEVICE_MANUFACTURER,
            configuration_url=DEVICE_CONFIGURATION_URL,
            model=f"Sensor {self.device.model}",
            sw_version=self.device.sw_version,
            via_device=(DOMAIN, self.gateway.unique_id),
        )

    async def get_value(self):
        """Return the sensor value from the api"""
        id = str(
            self.api_id
        )  # Specifically convert the id to a string for json to work properly

        resp = await self.api.get_sensor_data(id)
        _LOGGER.info(f"value: {resp['measurements'][id]['value']}")

        return resp["measurements"][id]["value"]

    async def async_update(self) -> None:
        """Get the sensors latest data"""

        self._attr_native_value = await self.get_value()
        _LOGGER.info(f"Return Value for Sensor: {self.name}: {self.state}")

    async def async_added_to_hass(self) -> None:
        """Call when entity about to be added to hass."""
        await super().async_added_to_hass()
        state = await self.async_get_last_sensor_data()
        if state:
            self._attr_native_value = state.native_value
