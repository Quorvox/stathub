"""Steam GCPD история ММ / Премьер — как на твоём скрине.
Важно честно: официального Web API для неё НЕТ.
Страница https://steamcommunity.com/id/<vanity>/gcpd/730/?tab=matchhistorypremier
отдаётся только залогиненному браузеру (Game Coordinator, приватная).
Варианты как её получить:
  1. FACEIT API — только FACEIT-матчи (уже есть во вкладке FACEIT).
  2. Leetify / CSStats — авто-разбор демок (нужен их API/парсинг демок).
  3. Этот модуль: качает ту же gcpd-страницу через твою cookie steamLoginSecure.
     Без cookie Steam вернёт страницу логина — тогда покажем инструкцию.
Табы Steam: matchhistorypremier, matchhistorycompetitive, matchhistoryscrimmage, etc.
"""
import re
import requests

TABS = {
    "premier": "matchhistorypremier",
    "competitive": "matchhistorycompetitive",
    "wingman": "matchhistorywingman",
}

BASE_GCPD = "https://steamcommunity.com/id/{vanity}/gcpd/730/"


def build_urls(vanity: str) -> dict:
    base = BASE_GCPD.format(vanity=vanity)
    return {k: f"{base}?tab={v}" for k, v in TABS.items()}


def fetch_tab(vanity: str, tab: str, cookies: dict | None = None) -> dict:
    """Пробует скачать gcpd-таб. Возвращает {'ok': bool, 'html': str, 'need_login': bool}."""
    tab_param = TABS.get(tab, tab)
    url = f"{BASE_GCPD.format(vanity=vanity)}?tab={tab_param}"
    try:
        r = requests.get(url, cookies=cookies or {}, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) StatHub/1.0",
        }, timeout=15)
    except Exception as e:
        return {"ok": False, "html": "", "need_login": False, "error": str(e), "url": url}
    html = r.text or ""
    need_login = ("Sign In" in html and "steamLogin" in html) or "login" in html[:2000].lower() and "matchhistory" not in html.lower()
    # эвристика: если в html нет Match Results и есть login-form — нужен логин
    if "Match Results" not in html and ("g_steamID" not in html):
        # всё равно отдаём html для отладки, но помечаем
        pass
    return {"ok": r.status_code == 200, "html": html, "need_login": need_login, "url": url, "status": r.status_code}


def parse_summary_from_html(html: str) -> list:
    """Грубая выжимка K/D/A/HS из gcpd-html без bs4 (чтобы не тянуть зависимости).
    Возвращает список строк таблицы. Если не залогинен — вернёт []."""
    if not html or "Match Results" not in html:
        return []
    # ищем строки вида Player Name ... Ping K A D ... HSP Score — берём текстовые куски
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text)
    # отдаём первые 2000 символов для отладки в UI
    return [text[i:i+500] for i in range(0, min(len(text), 2000), 500)]


COOKIE_HELP = (
    "Steam не даёт ММ/Премьер историю через публичный API — только через браузер с логином.\n"
    "Как подключить её в StatHub:\n"
    "1. Открой в Chrome: https://steamcommunity.com/id/<vanity>/gcpd/730/?tab=matchhistorypremier\n"
    "2. F12 -> Application -> Cookies -> скопируй steamLoginSecure\n"
    "3. Вставь его в Настройки -> Steam cookie. После этого StatHub сможет качать ту же таблицу.\n"
    "Пока ключа нет — пользуйся вкладкой FACEIT (там тоже K/D, HS%, счёт) + Steam-обзором."
)
