"""Weather for the masthead: Open-Meteo geocoding + forecast (no API key), cached per city/day."""

from datetime import date
from typing import Any

import httpx
import structlog
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import WeatherCache

log = structlog.get_logger(__name__)

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

# WMO weather interpretation codes, grouped the way a newspaper would say them
_CONDITIONS: tuple[tuple[range, str], ...] = (
    (range(0, 1), "Clear"),
    (range(1, 3), "Mostly clear"),
    (range(3, 4), "Overcast"),
    (range(45, 49), "Fog"),
    (range(51, 58), "Drizzle"),
    (range(61, 68), "Rain"),
    (range(71, 78), "Snow"),
    (range(80, 83), "Showers"),
    (range(85, 87), "Snow showers"),
    (range(95, 100), "Thunderstorms"),
)


class Weather(BaseModel):
    city: str
    condition: str
    temp_max_c: int
    temp_min_c: int


def describe(code: int) -> str:
    return next((label for codes, label in _CONDITIONS if code in codes), "Mixed")


def city_key(city: str) -> str:
    return " ".join(city.lower().split())[:120]


def parse_forecast(city: str, payload: dict[str, Any]) -> Weather:
    daily = payload["daily"]
    return Weather(
        city=city,
        condition=describe(int(daily["weather_code"][0])),
        temp_max_c=round(daily["temperature_2m_max"][0]),
        temp_min_c=round(daily["temperature_2m_min"][0]),
    )


class WeatherService:
    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def _fetch(self, city: str) -> Weather | None:
        geo = await self._client.get(
            GEOCODE_URL, params={"name": city, "count": 1, "language": "en", "format": "json"}
        )
        geo.raise_for_status()
        results = geo.json().get("results") or []
        if not results:
            log.info("weather_city_not_found", city=city)
            return None
        place = results[0]
        forecast = await self._client.get(
            FORECAST_URL,
            params={
                "latitude": place["latitude"],
                "longitude": place["longitude"],
                "daily": "weather_code,temperature_2m_max,temperature_2m_min",
                "timezone": "auto",
                "forecast_days": 1,
            },
        )
        forecast.raise_for_status()
        return parse_forecast(place.get("name", city), forecast.json())

    async def for_city(self, session: AsyncSession, city: str | None, day: date) -> Weather | None:
        """Today's weather for a city; None when unknown or Open-Meteo is unreachable."""
        if not city or not city.strip():
            return None
        key = city_key(city)
        cached = await session.scalar(
            select(WeatherCache.data).where(WeatherCache.city_key == key, WeatherCache.day == day)
        )
        if cached is not None:
            return Weather.model_validate(cached)
        try:
            weather = await self._fetch(city.strip())
        except (httpx.HTTPError, KeyError, IndexError, ValueError):
            log.warning("weather_fetch_failed", city=city, exc_info=True)
            return None
        if weather is not None:
            await session.execute(
                insert(WeatherCache)
                .values(city_key=key, day=day, data=weather.model_dump())
                .on_conflict_do_nothing(index_elements=["city_key", "day"])
            )
            await session.flush()
        return weather
