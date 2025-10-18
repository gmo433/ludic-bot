# Optional helper module for API-Sport interactions.
# Currently the main code uses direct requests; you can extend here.
import os
import requests
from datetime import datetime, timedelta

API_SPORT_KEY = os.getenv("API_SPORT_KEY")
BASE = "https://app.api-sport.ru/api/football"

def fetch_matches_within(hours=2):
    now = datetime.utcnow()
    to = now + timedelta(hours=hours)
    params = {
        "from": now.strftime("%Y-%m-%d %H:%M:%S"),
        "to": to.strftime("%Y-%m-%d %H:%M:%S"),
        "timezone": "UTC"
    }
    headers = {"X-API-KEY": API_SPORT_KEY}
    url = f"{BASE}/matches"
    r = requests.get(url, headers=headers, params=params, timeout=10)
    r.raise_for_status()
    return r.json()
