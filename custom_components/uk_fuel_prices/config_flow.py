"""Config flow for UK Fuel Prices integration."""
import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback

from .const import (
    DOMAIN,
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_POSTCODES,
    FUEL_TYPES,
    DEFAULT_RADIUS,
    DEFAULT_FUEL_TYPE,
)

_LOGGER = logging.getLogger(__name__)


class UKFuelPricesConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for UK Fuel Prices."""

    VERSION = 1

    def __init__(self):
        self._client_id = None
        self._client_secret = None
        self._postcodes = []

    async def async_step_user(self, user_input=None):
        """Handle the initial step — API credentials."""
        errors = {}
        if user_input is not None:
            self._client_id = user_input[CONF_CLIENT_ID]
            self._client_secret = user_input[CONF_CLIENT_SECRET]
            return await self.async_step_postcodes()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_CLIENT_ID): str,
                vol.Required(CONF_CLIENT_SECRET): str,
            }),
            errors=errors,
        )

    async def async_step_postcodes(self, user_input=None):
        """Handle adding postcodes."""
        errors = {}
        if user_input is not None:
            postcode = user_input.get("postcode", "").strip().upper()
            radius = user_input.get("radius", DEFAULT_RADIUS)
            fuel_type = user_input.get("fuel_type", DEFAULT_FUEL_TYPE)

            if postcode:
                self._postcodes.append({
                    "postcode": postcode,
                    "radius": radius,
                    "fuel_type": fuel_type,
                })

            add_another = user_input.get("add_another", False)
            if add_another:
                return await self.async_step_postcodes()

            if not self._postcodes:
                errors["postcode"] = "at_least_one"
            else:
                return self.async_create_entry(
                    title="UK Fuel Prices",
                    data={
                        CONF_CLIENT_ID: self._client_id,
                        CONF_CLIENT_SECRET: self._client_secret,
                    },
                    options={
                        CONF_POSTCODES: self._postcodes,
                    },
                )

        fuel_type_options = {k: v for k, v in FUEL_TYPES.items()}

        return self.async_show_form(
            step_id="postcodes",
            data_schema=vol.Schema({
                vol.Required("postcode"): str,
                vol.Optional("radius", default=DEFAULT_RADIUS): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=20)
                ),
                vol.Optional("fuel_type", default=DEFAULT_FUEL_TYPE): vol.In(fuel_type_options),
                vol.Optional("add_another", default=False): bool,
            }),
            errors=errors,
            description_placeholders={
                "count": str(len(self._postcodes)),
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return UKFuelPricesOptionsFlow(config_entry)


class UKFuelPricesOptionsFlow(config_entries.OptionsFlow):
    """Handle options for UK Fuel Prices."""

    def __init__(self, config_entry):
        self._config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage postcodes."""
        postcodes = self._config_entry.options.get(CONF_POSTCODES, [])
        postcode_list = ", ".join(p["postcode"] for p in postcodes) or "None"

        if user_input is not None:
            action = user_input.get("action")
            if action == "add":
                return await self.async_step_add_postcode()
            elif action == "remove":
                return await self.async_step_remove_postcode()

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required("action"): vol.In({
                    "add": "Add a postcode",
                    "remove": "Remove a postcode",
                }),
            }),
            description_placeholders={"postcodes": postcode_list},
        )

    async def async_step_add_postcode(self, user_input=None):
        """Add a new postcode."""
        if user_input is not None:
            postcode = user_input.get("postcode", "").strip().upper()
            radius = user_input.get("radius", DEFAULT_RADIUS)
            fuel_type = user_input.get("fuel_type", DEFAULT_FUEL_TYPE)

            postcodes = list(self._config_entry.options.get(CONF_POSTCODES, []))
            postcodes.append({
                "postcode": postcode,
                "radius": radius,
                "fuel_type": fuel_type,
            })
            return self.async_create_entry(title="", data={CONF_POSTCODES: postcodes})

        fuel_type_options = {k: v for k, v in FUEL_TYPES.items()}
        return self.async_show_form(
            step_id="add_postcode",
            data_schema=vol.Schema({
                vol.Required("postcode"): str,
                vol.Optional("radius", default=DEFAULT_RADIUS): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=20)
                ),
                vol.Optional("fuel_type", default=DEFAULT_FUEL_TYPE): vol.In(fuel_type_options),
            }),
        )

    async def async_step_remove_postcode(self, user_input=None):
        """Remove a postcode."""
        postcodes = list(self._config_entry.options.get(CONF_POSTCODES, []))

        if user_input is not None:
            to_remove = user_input.get("postcode")
            postcodes = [p for p in postcodes if p["postcode"] != to_remove]
            return self.async_create_entry(title="", data={CONF_POSTCODES: postcodes})

        postcode_options = {p["postcode"]: f"{p['postcode']} ({FUEL_TYPES.get(p.get('fuel_type', ''), p.get('fuel_type', ''))})" for p in postcodes}
        if not postcode_options:
            return self.async_abort(reason="no_postcodes")

        return self.async_show_form(
            step_id="remove_postcode",
            data_schema=vol.Schema({
                vol.Required("postcode"): vol.In(postcode_options),
            }),
        )
