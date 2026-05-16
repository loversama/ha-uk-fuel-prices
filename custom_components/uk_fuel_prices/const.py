"""Constants for UK Fuel Prices integration."""

DOMAIN = "uk_fuel_prices"
API_BASE = "https://www.developer.fuel-finder.service.gov.uk"

CONF_CLIENT_ID = "client_id"
CONF_CLIENT_SECRET = "client_secret"
CONF_POSTCODES = "postcodes"

FUEL_TYPES = {
    "B7_STANDARD": "Diesel",
    "E10": "Petrol (E10)",
    "E5": "Petrol (E5/Super)",
    "B7_PREMIUM": "Premium Diesel",
    "B10": "Biodiesel (B10)",
}

DEFAULT_RADIUS = 3
DEFAULT_FUEL_TYPE = "B7_STANDARD"
SCAN_INTERVAL_MINUTES = 30
BATCH_DELAY_SECONDS = 1.5
