"""League of Legends через официальный Riot Games API.
Ключ: https://developer.riotgames.com -> Log in -> Get API Key (development — на 24ч).
Цепочка: Riot ID (Name#TAG) -> PUUID [account-v1] -> match ids [match-v5] -> детали матча.
routing: asia (для KR/JP), europe (EU), americas (NA). platform: kr, euw1, ru? -> euw1 и т.д.
"""
import requests


def _headers(api_key: str) -> dict:
    return {"X-Riot-Token": api_key}


def need_key(api_key: str):
    if not api_key or len(api_key) < 10:
        raise RuntimeError(
            "Нет Riot API ключа. Получи бесплатный на developer.riotgames.com "
            "(Development key живёт 24 часа) и вставь во вкладку 'Настройки'."
        )


def split_riot_id(riot_id: str) -> tuple[str, str]:
    if "#" not in riot_id:
        raise RuntimeError("Riot ID должен быть вида Name#TAG (имя#тег).")
    name, tag = riot_id.split("#", 1)
    return name.strip(), tag.strip()


def get_account(game_name: str, tag: str, routing: str, api_key: str) -> dict:
    need_key(api_key)
    url = f"https://{routing}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{game_name}/{tag}"
    r = requests.get(url, headers=_headers(api_key), timeout=10)
    if r.status_code in (401, 403):
        raise RuntimeError("Riot 401/403: ключ неверный или истёк (dev-ключи живут 24ч — перевыпусти).")
    if r.status_code == 404:
        raise RuntimeError(f"Riot ID {game_name}#{tag} не найден в регионе {routing}. Попробуй routing europe/asia/americas.")
    if r.status_code == 429:
        raise RuntimeError("Riot 429: превышен лимит запросов, подожди минуту.")
    r.raise_for_status()
    return r.json()  # puuid, gameName, tagLine


def get_match_ids(puuid: str, routing: str, api_key: str, count: int = 15) -> list:
    need_key(api_key)
    url = f"https://{routing}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids"
    r = requests.get(url, params={"start": 0, "count": count}, headers=_headers(api_key), timeout=10)
    r.raise_for_status()
    return r.json()


def get_match(match_id: str, routing: str, api_key: str) -> dict:
    url = f"https://{routing}.api.riotgames.com/lol/match/v5/matches/{match_id}"
    r = requests.get(url, headers=_headers(api_key), timeout=10)
    r.raise_for_status()
    return r.json()


def get_summoner_by_puuid(puuid: str, platform: str, api_key: str) -> dict:
    need_key(api_key)
    url = f"https://{platform}.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}"
    r = requests.get(url, headers=_headers(api_key), timeout=10)
    if r.status_code == 404:
        return {}
    r.raise_for_status()
    return r.json()


def get_rank(summoner_id: str, platform: str, api_key: str) -> list:
    url = f"https://{platform}.api.riotgames.com/lol/league/v4/entries/by-summoner/{summoner_id}"
    r = requests.get(url, headers=_headers(api_key), timeout=10)
    if r.status_code == 404:
        return []
    r.raise_for_status()
    return r.json()


def summarise_matches(matches: list, puuid: str) -> dict:
    """Средние KDA, winrate по скачанным матчам."""
    wins = kills = deaths = assists = 0
    n = 0
    for m in matches:
        try:
            parts = m["info"]["participants"]
            me = next(p for p in parts if p.get("puuid") == puuid)
            n += 1
            wins += 1 if me.get("win") else 0
            kills += me.get("kills", 0)
            deaths += me.get("deaths", 0)
            assists += me.get("assists", 0)
        except Exception:
            continue
    if not n:
        return {"matches": 0}
    return {
        "matches": n,
        "winrate": round(wins / n * 100, 1),
        "avg_kills": round(kills / n, 1),
        "avg_deaths": round(deaths / n, 1),
        "avg_assists": round(assists / n, 1),
        "kda": round((kills + assists) / max(deaths, 1), 2),
    }
