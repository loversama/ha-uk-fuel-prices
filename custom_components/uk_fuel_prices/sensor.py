"""Sensor platform for UK Fuel Prices."""
import logging

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, CONF_POSTCODES, FUEL_TYPES
from .coordinator import FuelPriceCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up fuel price sensors from a config entry."""
    coordinator: FuelPriceCoordinator = hass.data[DOMAIN][entry.entry_id]
    postcodes = entry.options.get(CONF_POSTCODES, [])

    sensors = []
    for pc in postcodes:
        postcode = pc["postcode"]
        fuel_type = pc.get("fuel_type", "B7_STANDARD")
        sensors.append(FuelPriceSensor(coordinator, postcode, fuel_type, entry.entry_id))

    async_add_entities(sensors, True)


class FuelPriceSensor(CoordinatorEntity, SensorEntity):
    """Sensor showing cheapest fuel price for a postcode area."""

    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "p/L"
    _attr_icon = "mdi:gas-station"

    def __init__(self, coordinator: FuelPriceCoordinator, postcode: str, fuel_type: str, entry_id: str):
        super().__init__(coordinator)
        self._postcode = postcode
        self._fuel_type = fuel_type
        slug = postcode.replace(" ", "").lower()
        fuel_slug = fuel_type.lower().replace("_", "")
        self._attr_unique_id = f"uk_fuel_{slug}_{fuel_slug}"
        fuel_name = FUEL_TYPES.get(fuel_type, fuel_type)
        self._attr_name = f"{fuel_name} {postcode}"

    @property
    def native_value(self):
        if not self.coordinator.data:
            return None
        area_data = self.coordinator.data.get(self._postcode, {})
        stations = area_data.get("stations", [])
        if not stations:
            return None
        return stations[0]["price"]

    @property
    def extra_state_attributes(self):
        if not self.coordinator.data:
            return {}
        area_data = self.coordinator.data.get(self._postcode, {})
        stations = area_data.get("stations", [])
        if not stations:
            return {"station_name": "No data", "stations": []}

        cheapest = stations[0]
        avg = round(sum(s["price"] for s in stations) / len(stations), 1) if stations else None

        return {
            "postcode": self._postcode,
            "fuel_type": FUEL_TYPES.get(self._fuel_type, self._fuel_type),
            "station_name": cheapest["name"],
            "station_distance_miles": cheapest["distance"],
            "is_supermarket": cheapest["is_supermarket"],
            "area_average": avg,
            "station_count": len(stations),
            "stations": stations,
        }
