"""FACEIT Data API v4 — настоящие КД / HS% / ELO / история матчей CS2.
Ключ бесплатно: https://developers.faceit.com -> Create App -> Server key.
Без ключа модуль вернёт понятную ошибку, Steam-стата продолжит работать.
"""
import requests

BASE = "https://open.faceit.com/data/v4"


def _h(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def need_token(token: str):
    if not token or len(token) < 10:
        raise RuntimeError(
            "Нет FACEIT API ключа. Steam даёт только суммарную стату (киллы/смерти), "
            "а КД по матчам, ELO и историю последних 20 игр даёт только FACEIT. "
            "Получи бесплатный ключ: developers.faceit.com -> Docs -> API Key, "
            "вставь во вкладку 'Настройки'."
        )


def search_player(nickname: str, token: str) -> dict:
    need_token(token)
    r = requests.get(f"{BASE}/players", params={"nickname": nickname}, headers=_h(token), timeout=10)
    if r.status_code == 404:
        raise RuntimeError(f"FACEIT игрок '{nickname}' не найден.")
    r.raise_for_status()
    return r.json()


def lifetime_cs2(player_id: str, token: str) -> dict:
    """Поля: K/D Ratio, Win Rate %, Average Headshots %, Matches, ADR и т.д."""
    need_token(token)
    r = requests.get(f"{BASE}/players/{player_id}/stats/cs2", headers=_h(token), timeout=10)
    if r.status_code == 404:
        # у старых акков игра называется csgo
        r = requests.get(f"{BASE}/players/{player_id}/stats/csgo", headers=_h(token), timeout=10)
    r.raise_for_status()
    return r.json()


def match_history(player_id: str, token: str, limit: int = 20) -> list:
    need_token(token)
    r = requests.get(
        f"{BASE}/players/{player_id}/history",
        params={"game": "cs2", "offset": 0, "limit": limit},
        headers=_h(token),
        timeout=10,
    )
    r.raise_for_status()
    return r.json().get("items", [])


def parse_lifetime(lifetime: dict) -> dict:
    """Достаёт lifetime{} из ответа FACEIT в плоский словарь."""
    try:
        segs = lifetime.get("segments", [])
        life = next((s for s in segs if s.get("mode") == "5v5" or s.get("label") == "Lifetime"), segs[0] if segs else {})
        return (life.get("stats") or {})
    except Exception:
        return {}
