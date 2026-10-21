"""Dota 2 через бесплатный OpenDota (без ключа).
account_id = SteamID64 - 76561197960265728.
"""
import requests

BASE = "https://api.opendota.com/api"


def get_profile(account_id: str | int) -> dict:
    r = requests.get(f"{BASE}/players/{account_id}", timeout=15)
    if r.status_code == 404:
        raise RuntimeError(
            f"Dota-профиль {account_id} не найден в OpenDota. "
            "Это нормально если в Доту не играл / профиль скрыт. "
            "Проверь friend ID в Доте (Друзья -> Добавить) и вставь в Настройки."
        )
    r.raise_for_status()
    return r.json()


def get_wl(account_id: str | int) -> dict:
    r = requests.get(f"{BASE}/players/{account_id}/wl", timeout=15)
    r.raise_for_status()
    return r.json()


def get_recent(account_id: str | int, limit: int = 20) -> list:
    r = requests.get(f"{BASE}/players/{account_id}/recentMatches", timeout=15)
    r.raise_for_status()
    return r.json()[:limit]


def get_heroes(account_id: str | int) -> list:
    r = requests.get(f"{BASE}/players/{account_id}/heroes", timeout=15)
    r.raise_for_status()
    return r.json()


def summarise(profile: dict, wl: dict) -> dict:
    wins = wl.get("win", 0)
    lose = wl.get("lose", 0)
    total = wins + lose
    return {
        "name": (profile.get("profile") or {}).get("personaname", "—"),
        "mmr": (profile.get("mmr_estimate") or {}).get("estimate", "—"),
        "rank_tier": (profile.get("rank_tier") or "—"),
        "wins": wins,
        "losses": lose,
        "winrate": round(wins / total * 100, 1) if total else 0,
        "total": total,
    }
