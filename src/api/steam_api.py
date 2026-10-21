"""Steam Web API: резолв vanity -> SteamID64 + CS2 стата (appid 730)."""
import requests

BASE = "https://api.steampowered.com"


def resolve_vanity(vanity: str, api_key: str) -> str:
    """vanity (s1mple) -> '7656119...'. Бросает RuntimeError с понятным текстом."""
    url = f"{BASE}/ISteamUser/ResolveVanityURL/v0001/"
    r = requests.get(url, params={"key": api_key, "vanityurl": vanity}, timeout=10)
    if r.status_code != 200:
        raise RuntimeError(f"Steam вернул {r.status_code}: проверь API-ключ.")
    data = r.json().get("response", {})
    if data.get("success") == 1:
        return data["steamid"]
    # success=42 = не найдено (частая ошибка — ввели логин вместо vanity)
    raise RuntimeError(
        f"Профиль '{vanity}' не найден (success=42). "
        "Похоже, это логин аккаунта, а в API нужен vanity из URL "
        "(steamcommunity.com/id/<vanity>) или SteamID64."
    )


def resolve_steam_id(user_input: str, api_key: str) -> str:
    """Принимает URL / vanity / SteamID64, возвращает SteamID64."""
    from src.utils.helpers import parse_steam_input
    parsed = parse_steam_input(user_input)
    if parsed["type"] == "id64":
        return parsed["value"]
    if not parsed["value"]:
        raise RuntimeError("Введи Steam URL, vanity или SteamID64.")
    return resolve_vanity(parsed["value"], api_key)


def get_player_summary(steam_id64: str, api_key: str) -> dict:
    url = f"{BASE}/ISteamUser/GetPlayerSummaries/v0002/"
    r = requests.get(url, params={"key": api_key, "steamids": steam_id64}, timeout=10)
    r.raise_for_status()
    players = r.json().get("response", {}).get("players", [])
    return players[0] if players else {}


def get_cs2_stats(steam_id64: str, api_key: str) -> dict:
    """Возвращает dict {stat_name: value} для CS2 (730)."""
    url = f"{BASE}/ISteamUserStats/GetUserStatsForGame/v0002/"
    r = requests.get(url, params={"appid": 730, "key": api_key, "steamid": steam_id64}, timeout=15)
    if r.status_code == 403:
        raise RuntimeError("Профиль/статистика CS2 скрыта приватностью. Открой: Steam -> Профиль -> Настройки приватности -> 'Моя статистика' = Открытая.")
    if r.status_code == 400:
        raise RuntimeError("400 Bad Request: неверный steamid. Используй числовой SteamID64, а не логин.")
    r.raise_for_status()
    items = r.json().get("playerstats", {}).get("stats", [])
    return {s["name"]: s["value"] for s in items}


def get_recently_played(steam_id64: str, api_key: str, count: int = 10) -> list:
    url = f"{BASE}/IPlayerService/GetRecentlyPlayedGames/v1/"
    r = requests.get(url, params={"key": api_key, "steamid": steam_id64, "count": count}, timeout=10)
    if r.status_code == 400:
        raise RuntimeError("400: steamid должен быть числовым SteamID64 (17 цифр, начинается с 765...).")
    r.raise_for_status()
    return r.json().get("response", {}).get("games", [])
