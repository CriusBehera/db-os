"""Fetch real weather from Open-Meteo (free, no API key needed)."""
import json
import urllib.parse
import urllib.request


def _get_json(url, params, tries=3):
    full_url = url + "?" + urllib.parse.urlencode(params)
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(full_url, timeout=20) as r:
                return json.load(r)
        except OSError:  # network hiccup: try again, give up on the last attempt
            if attempt == tries - 1:
                raise


def find_city(name):
    """Look up a city by name. Returns (name, country, lat, lon) or None."""
    data = _get_json(
        "https://geocoding-api.open-meteo.com/v1/search", {"name": name, "count": 1}
    )
    if not data.get("results"):
        return None
    c = data["results"][0]
    return c["name"], c.get("country", ""), c["latitude"], c["longitude"]


def fetch_daily(lat, lon, past_days=30):
    """Daily weather for the last `past_days` days plus today.

    Returns a list of (date, temp_max, temp_min, rainfall_mm, wind_kmh).
    """
    data = _get_json(
        "https://api.open-meteo.com/v1/forecast",
        {
            "latitude": lat,
            "longitude": lon,
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max",
            "past_days": past_days,
            "forecast_days": 1,
            "timezone": "auto",
        },
    )["daily"]
    return list(zip(
        data["time"],
        data["temperature_2m_max"],
        data["temperature_2m_min"],
        data["precipitation_sum"],
        data["wind_speed_10m_max"],
    ))
