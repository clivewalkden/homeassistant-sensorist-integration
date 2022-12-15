import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import TEMP_CELSIUS, UnitOfElectricPotential, PERCENTAGE
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
                entities.append(device_sensor)
                known_probes.add(device["id"])

            for sensor in device["devices"]:
                if sensor["id"] in known_probes:
                    continue
                entities.append(SensoristSensor(sensor, device_sensor, api))
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

    def __init__(self, data, device: SensoristDevice, api: SensoristApi) -> None:
        """Initialize the SensoristSensor"""
        self.data = data
        self.device = device
        self.api = api

    @property
    def name(self):
        """Return the Sensor name"""
        if self.data["type"]["name"] == "batt":
            return None
        else:
            # return f"{self.device.name} {self.data['title']}"
            return f"{self.data['title']}"

    @property
    def state_class(self):
        return SensorStateClass.MEASUREMENT

    @property
    def device_class(self) -> SensorDeviceClass:
        if self.data["type"]["name"] == "temp":
            return SensorDeviceClass.TEMPERATURE
        elif self.data["type"]["name"] == "humi":
            return SensorDeviceClass.HUMIDITY
        elif self.data["type"]["name"] == "wireless":
            return SensorDeviceClass.POWER_FACTOR
        elif self.data["type"]["name"] == "batt":
            return SensorDeviceClass.VOLTAGE

    @property
    def native_unit_of_measurement(self) -> str:
        if self.data["type"]["name"] == "temp":
            return TEMP_CELSIUS
        elif self.data["type"]["name"] == "humi":
            return PERCENTAGE
        elif self.data["type"]["name"] == "wireless":
            return PERCENTAGE
        elif self.data["type"]["name"] == "batt":
            return UnitOfElectricPotential.VOLT

    @property
    def unique_id(self) -> str:
        return f"sensorist.{self.device.unique_id}_{self.data['title'].lower}"

    @property
    def api_id(self) -> int:
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
        )

    async def get_value(self):
        """Return the sensor value"""
        id = str(
            self.api_id
        )  # Specifically convert the id to a string for json to work properly
        _LOGGER.info(f"self.name {self.name}")
        sensor_id = self.name.split(" ")
        _LOGGER.info(sensor_id)

        resp = await self.api.get_sensor_data(self.api_id)
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