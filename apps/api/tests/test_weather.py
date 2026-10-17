from datetime import date

import httpx
import pytest
import respx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.editions.weather import (
    FORECAST_URL,
    GEOCODE_URL,
    Weather,
    WeatherService,
    city_key,
    describe,
    parse_forecast,
)
from app.models import WeatherCache

DAY = date(2026, 10, 17)
GEO = {"results": [{"name": "Lahore", "latitude": 31.55, "longitude": 74.34}]}
FORECAST = {
    "daily": {
        "time": ["2026-10-17"],
        "weather_code": [1],
        "temperature_2m_max": [31.4],
        "temperature_2m_min": [18.6],
    }
}


def test_describe_groups_wmo_codes() -> None:
    assert [describe(c) for c in (0, 2, 3, 63, 95, 99, 77, 12)] == [
        "Clear", "Mostly clear", "Overcast", "Rain", "Thunderstorms", "Thunderstorms",
        "Snow", "Mixed",
    ]  # fmt: skip


def test_parse_forecast_rounds_temperatures() -> None:
    assert parse_forecast("Lahore", FORECAST) == Weather(
        city="Lahore", condition="Mostly clear", temp_max_c=31, temp_min_c=19
    )


def test_city_key_normalises() -> None:
    assert city_key("  New   York ") == "new york"


@pytest.mark.integration
@respx.mock
async def test_fetches_once_per_city_per_day(db: AsyncSession) -> None:
    geo = respx.get(GEOCODE_URL).mock(return_value=httpx.Response(200, json=GEO))
    forecast = respx.get(FORECAST_URL).mock(return_value=httpx.Response(200, json=FORECAST))
    async with httpx.AsyncClient() as client:
        service = WeatherService(client)
        first = await service.for_city(db, "Lahore", DAY)
        second = await service.for_city(db, " lahore ", DAY)
    assert first == second
    assert first is not None
    assert first.condition == "Mostly clear"
    assert geo.call_count == forecast.call_count == 1
    assert await db.scalar(select(func.count()).select_from(WeatherCache)) == 1


@pytest.mark.integration
@respx.mock
async def test_new_day_fetches_again(db: AsyncSession) -> None:
    geo = respx.get(GEOCODE_URL).mock(return_value=httpx.Response(200, json=GEO))
    respx.get(FORECAST_URL).mock(return_value=httpx.Response(200, json=FORECAST))
    async with httpx.AsyncClient() as client:
        service = WeatherService(client)
        await service.for_city(db, "Lahore", DAY)
        await service.for_city(db, "Lahore", date(2026, 10, 18))
    assert geo.call_count == 2


@pytest.mark.integration
@respx.mock
async def test_unknown_city_and_outages_give_none_and_cache_nothing(db: AsyncSession) -> None:
    respx.get(GEOCODE_URL).mock(return_value=httpx.Response(200, json={}))
    async with httpx.AsyncClient() as client:
        service = WeatherService(client)
        assert await service.for_city(db, "Nowheresville", DAY) is None
        assert await service.for_city(db, None, DAY) is None
        assert await service.for_city(db, "   ", DAY) is None
    respx.get(GEOCODE_URL).mock(return_value=httpx.Response(503))
    async with httpx.AsyncClient() as client:
        assert await WeatherService(client).for_city(db, "Lahore", DAY) is None
    assert await db.scalar(select(func.count()).select_from(WeatherCache)) == 0
