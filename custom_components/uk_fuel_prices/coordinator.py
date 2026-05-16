"""Data coordinator for UK Fuel Prices."""
import asyncio
import logging
import math
from datetime import timedelta

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DOMAIN,
    API_BASE,
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_POSTCODES,
    SCAN_INTERVAL_MINUTES,
    BATCH_DELAY_SECONDS,
)

_LOGGER = logging.getLogger(__name__)


def _haversine_miles(lat1, lon1, lat2, lon2):
    R = 3958.8
    to_rad = lambda x: x * math.pi / 180
    d_lat = to_rad(lat2 - lat1)
    d_lon = to_rad(lon2 - lon1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(to_rad(lat1)) * math.cos(to_rad(lat2)) * math.sin(d_lon / 2) ** 2
    )
    return 2 * R * math.asin(math.sqrt(a))


class FuelPriceCoordinator(DataUpdateCoordinator):
    """Coordinator to fetch fuel prices from the Fuel Finder API."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=SCAN_INTERVAL_MINUTES),
        )
        self._client_id = entry.data[CONF_CLIENT_ID]
        self._client_secret = entry.data[CONF_CLIENT_SECRET]
        self._postcodes = entry.options.get(CONF_POSTCODES, [])
        self._block_supermarkets = entry.options.get("block_supermarkets", False)
        self._token = None

    async def _async_update_data(self):
        """Fetch data from Fuel Finder API."""
        try:
            async with aiohttp.ClientSession() as session:
                await self._get_token(session)

                stations = await self._fetch_all_paged(session, "/api/v1/pfs")
                prices = await self._fetch_all_paged(session, "/api/v1/pfs/fuel-prices")

                station_map = {}
                for s in stations:
                    nid = s.get("node_id")
                    if not nid:
                        continue
                    loc = s.get("location", {})
                    lat = loc.get("latitude") or s.get("latitude")
                    lon = loc.get("longitude") or s.get("longitude")
                    try:
                        lat = float(lat)
                        lon = float(lon)
                    except (TypeError, ValueError):
                        continue
                    station_map[nid] = {
                        "name": s.get("brand_name") or s.get("trading_name") or "Unknown",
                        "is_supermarket": bool(s.get("is_supermarket_service_station")),
                        "lat": lat,
                        "lon": lon,
                        "fuel_prices": [],
                    }

                for p in prices:
                    nid = p.get("node_id")
                    if nid and nid in station_map:
                        station_map[nid]["fuel_prices"] = p.get("fuel_prices", [])

                result = {}
                for pc in self._postcodes:
                    postcode = pc["postcode"]
                    radius = pc.get("radius", 3)
                    fuel_type = pc.get("fuel_type", "B7_STANDARD").upper()

                    coords = await self._geocode(session, postcode)
                    if not coords:
                        result[postcode] = {"error": "Geocoding failed", "stations": []}
                        continue

                    nearby = []
                    for nid, st in station_map.items():
                        dist = _haversine_miles(coords[0], coords[1], st["lat"], st["lon"])
                        if dist > radius:
                            continue

                        price = None
                        for fp in st["fuel_prices"]:
                            ft = (fp.get("fuel_type") or "").upper()
                            if ft == fuel_type:
                                try:
                                    price = float(fp["price"])
                                except (TypeError, ValueError, KeyError):
                                    pass
                                break
                        if price is None or price <= 0:
                            continue

                        if self._block_supermarkets:
                            name_upper = st["name"].upper()
                            supermarket_brands = [
                                "TESCO", "ASDA", "MORRISONS", "SAINSBURY",
                                "COSTCO", "WAITROSE", "CO-OP", "COOP",
                            ]
                            if any(brand in name_upper for brand in supermarket_brands):
                                continue

                        nearby.append({
                            "name": st["name"],
                            "price": price,
                            "distance": round(dist, 1),
                            "is_supermarket": st["is_supermarket"],
                        })

                    nearby.sort(key=lambda x: x["price"])
                    result[postcode] = {
                        "fuel_type": fuel_type,
                        "stations": nearby[:10],
                    }

                return result

        except Exception as err:
            raise UpdateFailed(f"Error fetching fuel prices: {err}") from err

    async def _get_token(self, session: aiohttp.ClientSession):
        async with session.post(
            f"{API_BASE}/api/v1/oauth/generate_access_token",
            json={"client_id": self._client_id, "client_secret": self._client_secret},
            timeout=aiohttp.ClientTimeout(total=30),
        ) as resp:
            body = await resp.json()
            self._token = body.get("data", {}).get("access_token")
            if not self._token:
                raise UpdateFailed("Failed to obtain Fuel Finder access token")

    async def _fetch_all_paged(self, session: aiohttp.ClientSession, path: str):
        all_items = []
        for batch in range(1, 200):
            url = f"{API_BASE}{path}?batch-number={batch}"
            headers = {"Authorization": f"Bearer {self._token}"}
            try:
                async with session.get(
                    url, headers=headers, timeout=aiohttp.ClientTimeout(total=45)
                ) as resp:
                    if resp.status in (401, 403):
                        await self._get_token(session)
                        headers = {"Authorization": f"Bearer {self._token}"}
                        async with session.get(
                            url, headers=headers, timeout=aiohttp.ClientTimeout(total=45)
                        ) as retry_resp:
                            if retry_resp.status == 404:
                                break
                            page = await retry_resp.json()
                    elif resp.status == 404:
                        break
                    elif resp.status == 429:
                        _LOGGER.warning("Rate limited on %s batch %d, stopping", path, batch)
                        break
                    else:
                        page = await resp.json()
            except asyncio.TimeoutError:
                _LOGGER.warning("Timeout on %s batch %d", path, batch)
                break
            except Exception as e:
                _LOGGER.warning("Error on %s batch %d: %s", path, batch, e)
                break

            if not isinstance(page, list) or len(page) == 0:
                break
            all_items.extend(page)
            if len(page) < 100:
                break
            await asyncio.sleep(BATCH_DELAY_SECONDS)
        return all_items

    async def _geocode(self, session: aiohttp.ClientSession, postcode: str):
        url = f"https://api.postcodes.io/postcodes/{postcode.replace(' ', '%20')}"
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                data = await resp.json()
                if data.get("status") != 200:
                    return None
                return (data["result"]["latitude"], data["result"]["longitude"])
        except Exception:
            return None
