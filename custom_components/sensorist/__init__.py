"""The Sensorist Sensor Integration integration."""
from __future__ import annotations
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady, HomeAssistantError
from homeassistant.helpers.device_registry import DeviceEntry

from .const import DOMAIN
from .api import SensoristApi

PLATFORMS: list[Platform] = [Platform.SENSOR]

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Sensorist Sensor Integration from a config entry."""

    try:
        api = SensoristApi(entry.data[CONF_USERNAME], entry.data[CONF_PASSWORD])
        resp = await api.test()

        if not resp:
            _LOGGER.info(resp)
            raise InvalidAuth

        _LOGGER.info(resp)

    except CannotConnect as err:
        raise ConfigEntryNotReady from err
    except InvalidAuth as err:
        _LOGGER.error("Unable to authenticate with the Meater API: %s", err)
        return False

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault("known_probes", set())

    hass.data[DOMAIN][entry.entry_id] = {"api": api}

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
        hass.data[DOMAIN].pop("known_probes")

    return unload_ok


async def async_remove_config_entry_device(
    hass: HomeAssistant, config_entry: ConfigEntry, device_entry: DeviceEntry
) -> bool:
    """Remove a config entry from a device"""
    return True


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
