"""Общие помощники: разбор Steam-ввода, расчёты K/D, HS%, accuracy."""
import re


STEAM64_BASE = 76561197960265728


def parse_steam_input(text: str) -> dict:
    """Разбирает что ввёл юзер: URL, vanity или SteamID64.
    Возвращает {'type': 'id64'|'vanity', 'value': str}
    """
    text = (text or "").strip()
    if not text:
        return {"type": "vanity", "value": ""}
    # https://steamcommunity.com/profiles/7656.../
    m = re.search(r"/profiles/(\d{17})", text)
    if m:
        return {"type": "id64", "value": m.group(1)}
    # https://steamcommunity.com/id/Vanity/
    m = re.search(r"/id/([^/]+)", text)
    if m:
        return {"type": "vanity", "value": m.group(1)}
    # чисто цифры SteamID64
    if re.fullmatch(r"\d{17}", text) and text.startswith("765"):
        return {"type": "id64", "value": text}
    # vanity без пробелов. логин аккаунта сюда НЕ подходит
    # Логин нельзя использовать в API, нужно именно то что в URL после /id/
    return {"type": "vanity", "value": text}


def steam64_to_account_id(steam64: str | int) -> int:
    return int(steam64) - STEAM64_BASE


def calc_cs_derived(stats: dict) -> dict:
    kills = stats.get("total_kills", 0)
    deaths = stats.get("total_deaths", 1) or 1
    hs = stats.get("total_kills_headshot", 0)
    shots = stats.get("total_shots_fired", 0)
    # сумма всех total_hits_*
    hits = sum(v for k, v in stats.items() if k.startswith("total_hits_"))
    matches = stats.get("total_matches_played", 0)
    won = stats.get("total_matches_won", 0)
    rounds = stats.get("total_rounds_played", 0) or 1
    time_s = stats.get("total_time_played", 0)
    damage = stats.get("total_damage_done", 0)
    return {
        "kd": round(kills / deaths, 2) if deaths else kills,
        "hs_percent": round(hs / kills * 100, 1) if kills else 0,
        "accuracy": round(hits / shots * 100, 1) if shots else 0,
        "winrate": round(won / matches * 100, 1) if matches else 0,
        "hours": round(time_s / 3600, 1),
        "adr": round(damage / rounds, 1),
        "kills": kills,
        "deaths": deaths,
        "headshots": hs,
    }


def fmt_hours(h: float) -> str:
    return f"{h:,.1f} ч".replace(",", " ")
