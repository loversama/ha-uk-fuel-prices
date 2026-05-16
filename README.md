# UK Fuel Prices for Home Assistant

A Home Assistant custom integration that fetches live fuel prices from the [UK Government Fuel Finder API](https://www.fuel-finder.service.gov.uk).

## Features

- Monitor fuel prices for any number of UK postcodes
- Choose fuel type per postcode (Diesel, Petrol E10, Super E5, Premium Diesel)
- Configurable search radius per postcode
- Shows cheapest station with name, price, and distance
- Full station list in sensor attributes
- Updates every 30 minutes
- Full UI configuration (no YAML needed)

## Installation (HACS)

1. Open HACS in Home Assistant
2. Click the three dots menu → **Custom repositories**
3. Add `https://github.com/loversama/ha-uk-fuel-prices` as an **Integration**
4. Search for "UK Fuel Prices" and install
5. Restart Home Assistant
6. Go to **Settings → Devices & Services → Add Integration → UK Fuel Prices**

## Configuration

1. Enter your Fuel Finder API credentials (get them from https://www.fuel-finder.service.gov.uk)
2. Add postcodes with your preferred fuel type and search radius
3. Sensors are created automatically

## Sensors

Each postcode creates a sensor like `sensor.diesel_sw1a1aa`:
- **State**: Cheapest price (p/L)
- **Attributes**:
  - `station_name` — Name of the cheapest station
  - `station_distance_miles` — Distance to it
  - `is_supermarket` — Whether it's a supermarket station
  - `area_average` — Average price across all nearby stations
  - `stations` — Full list of up to 10 cheapest stations

## Dashboard Card

```yaml
type: entities
title: ⛽ Fuel Prices
entities:
  - entity: sensor.diesel_sw1a1aa
    secondary_info: attribute
    attribute: station_name
  - entity: sensor.diesel_ec1a1bb
    secondary_info: attribute
    attribute: station_name
```

## Managing Postcodes

Go to the integration's options (gear icon) to add or remove postcodes after initial setup.

## API Credentials

Register at https://www.fuel-finder.service.gov.uk to get a Client ID and Client Secret.
