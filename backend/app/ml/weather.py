"""Weather data via Open-Meteo (free, no API key required).

Two distinct, deliberately separate uses:

1. `fetch_uk_training_weather` — historical daily mean temperature for
   Loughborough, England (REFIT's actual monitoring location), joined onto
   the household forecaster's TRAINING data. This is a legitimate model
   feature: REFIT houses are real UK homes, so UK weather genuinely explains
   variance in their real consumption (heating load).

2. `fetch_tn_current_temperature` — live/forecast temperature for a Tamil
   Nadu city, used ONLY by the appliance-level heuristic adjustment in
   `app/ml/models/appliance_model.py` (AC/fan duty-cycle scaling). This is
   NOT fed into the REFIT-trained household forecaster — a model trained on
   UK heating behaviour has no learned relationship for cooling-driven load,
   so transplanting Chennai temperature into that model would be a false
   sense of precision. Keeping these two paths separate is intentional.
"""
import time

import pandas as pd
import requests

LOUGHBOROUGH_COORDS = (52.77, -1.21)
TN_CITY_COORDS = {
    "chennai": (13.08, 80.27),
    "coimbatore": (11.02, 76.96),
    "madurai": (9.93, 78.12),
    "tiruchirappalli": (10.79, 78.70),
    "salem": (11.66, 78.15),
}
DEFAULT_TN_CITY = "chennai"

REQUEST_TIMEOUT_SECONDS = 10


def fetch_uk_training_weather(start_date: str, end_date: str) -> pd.DataFrame:
    """
    Daily mean temperature (°C) for Loughborough over [start_date, end_date]
    (YYYY-MM-DD). Returns columns: date, temp_mean_c. Raises on failure —
    callers should decide whether to proceed without weather features.
    """
    lat, lon = LOUGHBOROUGH_COORDS
    resp = requests.get(
        "https://archive-api.open-meteo.com/v1/archive",
        params={
            "latitude": lat,
            "longitude": lon,
            "start_date": start_date,
            "end_date": end_date,
            "daily": "temperature_2m_mean",
            "timezone": "auto",
        },
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    resp.raise_for_status()
    daily = resp.json()["daily"]
    df = pd.DataFrame({"date": daily["time"], "temp_mean_c": daily["temperature_2m_mean"]})
    df["date"] = pd.to_datetime(df["date"])
    return df


def fetch_tn_current_temperature(city: str = DEFAULT_TN_CITY) -> float | None:
    """
    Today's forecast mean temperature (°C) for a Tamil Nadu city. Returns
    None on any failure (network, unknown city) so callers can gracefully
    fall back to a fixed comfort-baseline assumption instead of erroring.
    """
    coords = TN_CITY_COORDS.get(city.lower())
    if coords is None:
        return None
    lat, lon = coords
    try:
        resp = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat,
                "longitude": lon,
                "daily": "temperature_2m_mean",
                "timezone": "auto",
                "forecast_days": 1,
            },
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
        return float(resp.json()["daily"]["temperature_2m_mean"][0])
    except Exception:
        return None


_tn_temp_cache: dict[str, float | None] = {"value": None, "fetched_at": 0.0, "city": ""}
CACHE_TTL_SECONDS = 1800  # 30 min — a request-triggered fetch per optimizer call would be wasteful


def get_cached_tn_temperature(city: str = DEFAULT_TN_CITY) -> float | None:
    """
    Cached wrapper around `fetch_tn_current_temperature`. The optimizer calls
    appliance estimation many times per request (its search loop), so a raw
    per-call network fetch would add unacceptable latency — this refreshes
    at most once per CACHE_TTL_SECONDS, and falls back to the last known
    value (even if stale) rather than None when a refresh fails.
    """
    now = time.time()
    is_fresh = (
        _tn_temp_cache["city"] == city
        and now - _tn_temp_cache["fetched_at"] < CACHE_TTL_SECONDS
    )
    if is_fresh:
        return _tn_temp_cache["value"]

    fresh_value = fetch_tn_current_temperature(city)
    if fresh_value is not None:
        _tn_temp_cache.update(value=fresh_value, fetched_at=now, city=city)
        return fresh_value

    return _tn_temp_cache["value"]  # stale cache (or None) is better than crashing a request
