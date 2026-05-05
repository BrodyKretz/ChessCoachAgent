"""
Chess.com public API wrapper. No auth required — all data is public.
Fetches games by username, time control, and count.
"""
import requests
import time
from datetime import datetime, timedelta
from typing import Optional

BASE_URL = "https://api.chess.com/pub"
HEADERS = {"User-Agent": "ChessCoachAgent/1.0 (portfolio project)"}


def validate_user(username: str) -> Optional[dict]:
    """Return player profile or None if username doesn't exist."""
    try:
        resp = requests.get(f"{BASE_URL}/player/{username}", headers=HEADERS, timeout=10)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException:
        return None


def fetch_recent_games(username: str, time_control: str, num_games: int) -> list:
    """
    Fetch the most recent N games filtered by time control class.
    Looks back up to 6 months to find enough games.
    time_control: 'blitz' | 'bullet' | 'rapid' | 'daily' | 'all'
    """
    collected = []
    now = datetime.now()

    for months_back in range(6):
        if len(collected) >= num_games:
            break

        target = now - timedelta(days=30 * months_back)
        url = f"{BASE_URL}/player/{username}/games/{target.year}/{target.month:02d}"

        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            if resp.status_code == 404:
                continue
            resp.raise_for_status()
            games = resp.json().get("games", [])
        except requests.RequestException:
            continue

        if time_control != "all":
            games = [g for g in games if g.get("time_class") == time_control]

        collected.extend(games)
        time.sleep(0.4)

    # Games come in chronological order; take the most recent N
    recent = list(reversed(collected))[:num_games]
    return recent
