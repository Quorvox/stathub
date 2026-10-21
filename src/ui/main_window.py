"""StatHub v2: Главная с 3 дисциплинами + детали + сплэш.
Главная -> клик по CS2/Dota/LoL -> Обзор (быстрые КД/HS/винрейт) + Матчи подробно + линия ранга.
Видимость дисциплин — в Настройках (show_cs2/show_dota/show_lol).
"""
import json
import webbrowser
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QLabel, QLineEdit, QPushButton, QGridLayout, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QComboBox,
    QStackedWidget, QProgressBar, QCheckBox,
)

from src.api import steam_api, faceit_api, dota_api, riot_api, steam_gcpd
from src.utils.helpers import calc_cs_derived, steam64_to_account_id

ROOT = Path(__file__).resolve().parents[2]
SETTINGS = ROOT / "config" / "settings.json"

DARK = """
QMainWindow, QWidget { background: #14161d; color: #e8eaf0; font-size: 14px; }
QTabWidget::pane { border: 1px solid #2a2e3a; border-radius: 8px; }
QTabBar::tab { background: #1e222d; padding: 10px 18px; margin: 4px; border-radius: 8px; }
QTabBar::tab:selected { background: #f0a500; color: #111; font-weight: bold; }
QLineEdit, QComboBox { background: #1e222d; border: 1px solid #333a4d; border-radius: 8px; padding: 8px; }
QPushButton { background: #f0a500; color: #111; font-weight: bold; border-radius: 8px; padding: 9px 16px; }
QPushButton:hover { background: #ffb81c; }
QPushButton.nav { background: #1e222d; color: #e8eaf0; border: 1px solid #2a2e3a; }
QPushButton.nav:checked, QPushButton.nav:hover { background: #f0a500; color: #111; }
QTableWidget { background: #1a1e28; gridline-color: #2a2e3a; border-radius: 8px; }
QHeaderView::section { background: #232837; color: #f0a500; padding: 6px; border: none; }
QProgressBar { background: #1e222d; border: 1px solid #2a2e3a; border-radius: 8px; text-align: center; height: 18px; }
QProgressBar::chunk { background: #f0a500; border-radius: 6px; }
"""


def load_settings() -> dict:
    try:
        d = json.loads(SETTINGS.read_text(encoding="utf-8"))
    except Exception:
        d = {}
    d.setdefault("steam_api_key", "")
    d.setdefault("steam_input", "")
    d.setdefault("steam_id64", "")
    d.setdefault("faceit_api_key", "")
    d.setdefault("faceit_nickname", "")
    d.setdefault("dota_account_id", "")
    d.setdefault("riot_api_key", "")
    d.setdefault("riot_id", "")
    d.setdefault("riot_routing", "europe")
    d.setdefault("riot_platform", "euw1")
    d.setdefault("show_cs2", True)
    d.setdefault("show_dota", True)
    d.setdefault("show_lol", True)
    d.setdefault("steam_cookie", "")
    return d


def save_settings(d: dict):
    SETTINGS.parent.mkdir(exist_ok=True)
    SETTINGS.write_text(json.dumps(d, indent=2, ensure_ascii=False), encoding="utf-8")


class StatCard(QFrame):
    def __init__(self, title: str, value: str = "—"):
        super().__init__()
        self.setObjectName("card")
        self.setStyleSheet("QFrame#card { background:#1e222d; border:1px solid #2a2e3a; border-radius:12px; }")
        lay = QVBoxLayout(self)
        t = QLabel(title)
        t.setStyleSheet("color:#9aa0b4; font-size:12px;")
        self.v = QLabel(value)
        self.v.setStyleSheet("color:#fff; font-size:22px; font-weight:bold;")
        self.v.setWordWrap(True)
        lay.addWidget(t)
        lay.addWidget(self.v)

    def set(self, v: str):
        self.v.setText(str(v))


class RankLine(QFrame):
    """Линия ранга: подпись + прогресс-бар + коммент."""
    def __init__(self, title="Ранг"):
        super().__init__()
        self.setObjectName("rank")
        self.setStyleSheet("QFrame#rank { background:#1a1e28; border:1px solid #2a2e3a; border-radius:12px; }")
        lay = QVBoxLayout(self)
        self.t = QLabel(title)
        self.t.setStyleSheet("color:#f0a500; font-weight:bold;")
        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        self.info = QLabel("—")
        self.info.setStyleSheet("color:#9aa0b4; font-size:12px;")
        self.info.setWordWrap(True)
        lay.addWidget(self.t)
        lay.addWidget(self.bar)
        lay.addWidget(self.info)

    def set(self, title: str, pct: float, info: str):
        self.t.setText(title)
        self.bar.setValue(int(max(0, min(100, pct))))
        self.bar.setFormat(f"{pct:.1f}%")
        self.info.setText(info)


def make_table(cols: list[str]) -> QTableWidget:
    t = QTableWidget(0, len(cols))
    t.setHorizontalHeaderLabels(cols)
    t.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
    t.setEditTriggers(QTableWidget.NoEditTriggers)
    t.setAlternatingRowColors(True)
    return t


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("StatHub — CS2 • Dota 2 • LoL")
        self.resize(1120, 760)
        self.setStyleSheet(DARK)
        self.cfg = load_settings()

        root = QWidget()
        self.setCentralWidget(root)
        lay = QVBoxLayout(root)

        # верх: поиск + обновить
        top = QHBoxLayout()
        self.steam_input = QLineEdit(self.cfg.get("steam_input", ""))
        self.steam_input.setPlaceholderText("Steam URL / vanity / SteamID64 (напр. s1mple)")
        self.btn = QPushButton("↻ Обновить всё")
        self.btn.clicked.connect(self.refresh_all)
        top.addWidget(QLabel("Steam:"))
        top.addWidget(self.steam_input, 1)
        top.addWidget(self.btn)
        lay.addLayout(top)

        self.status = QLabel("Введи свой Steam и нажми «Обновить всё». Ключи API — во вкладке Настройки.")
        self.status.setStyleSheet("color:#9aa0b4;")
        self.status.setWordWrap(True)
        lay.addWidget(self.status)

        # навигация
        nav = QHBoxLayout()
        self.nav_btns = {}
        for key, txt in [("home", "🏠 Главная"), ("cs2", "🔫 CS2"), ("dota", "🛡 Dota 2"),
                         ("lol", "✨ LoL"), ("settings", "⚙ Настройки")]:
            b = QPushButton(txt)
            b.setCheckable(True)
            b.setProperty("class", "nav")
            b.setStyleSheet("QPushButton { background:#1e222d; color:#e8eaf0; border:1px solid #2a2e3a; border-radius:8px; padding:8px; } QPushButton:checked { background:#f0a500; color:#111; }")
            b.clicked.connect(lambda _=False, k=key: self.goto(k))
            nav.addWidget(b)
            self.nav_btns[key] = b
        lay.addLayout(nav)

        self.stack = QStackedWidget()
        lay.addWidget(self.stack, 1)

        self.page_home = self._build_home()
        self.page_cs2 = self._build_cs2()
        self.page_dota = self._build_dota()
        self.page_lol = self._build_lol()
        self.page_settings = self._build_settings()
        for p in [self.page_home, self.page_cs2, self.page_dota, self.page_lol, self.page_settings]:
            self.stack.addWidget(p)
        self.goto("home")
        self.apply_visibility()

    # НАВИГАЦИЯ
    def goto(self, key: str):
        idx = {"home": 0, "cs2": 1, "dota": 2, "lol": 3, "settings": 4}[key]
        self.stack.setCurrentIndex(idx)
        for k, b in self.nav_btns.items():
            b.setChecked(k == key)

    def apply_visibility(self):
        self.card_cs2.setVisible(bool(self.cfg.get("show_cs2", True)))
        self.card_dota.setVisible(bool(self.cfg.get("show_dota", True)))
        self.card_lol.setVisible(bool(self.cfg.get("show_lol", True)))
        self.nav_btns["cs2"].setVisible(bool(self.cfg.get("show_cs2", True)))
        self.nav_btns["dota"].setVisible(bool(self.cfg.get("show_dota", True)))
        self.nav_btns["lol"].setVisible(bool(self.cfg.get("show_lol", True)))

    # ГЛАВНАЯ
    def _discipline_card(self, emoji: str, name: str, desc: str, page: str):
        f = QFrame()
        f.setObjectName("disc")
        f.setStyleSheet("QFrame#disc { background:#1a1e28; border:1px solid #2a2e3a; border-radius:16px; }"
                        "QFrame#disc:hover { border-color:#f0a500; }"
                        "QFrame#disc > QLabel { background:transparent; }")
        f.setMinimumHeight(230)
        lay = QVBoxLayout(f)
        lay.setContentsMargins(20, 18, 20, 18)
        lay.setSpacing(10)
        t = QLabel(f"{emoji}  {name}")
        t.setStyleSheet("font-size:22px; font-weight:bold; color:#f0a500;")
        d = QLabel(desc)
        d.setStyleSheet("color:#9aa0b4;")
        d.setWordWrap(True)
        quick = QLabel("Нажми «Обновить всё» — тут будет K/D, HS%, винрейт.")
        quick.setStyleSheet("font-size:13px; background:#232837; border-radius:8px; padding:10px;")
        quick.setWordWrap(True)
        b = QPushButton("Открыть →")
        b.clicked.connect(lambda: self.goto(page))
        lay.addWidget(t)
        lay.addWidget(d)
        lay.addWidget(quick)
        lay.addStretch(1)
        lay.addWidget(b)
        return f, quick

    def _build_home(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(4, 16, 4, 4)
        title = QLabel("StatHub")
        title.setStyleSheet("font-size:34px; font-weight:800; color:#fff;")
        hl = QLabel("Вся твоя стата из CS2, Dota 2 и LoL в одном окне. Выбери дисциплину: внутри K/D, HS%, винрейт, матчи и линия ранга.")
        hl.setStyleSheet("color:#9aa0b4; font-size:14px;")
        hl.setWordWrap(True)
        lay.addWidget(title)
        lay.addWidget(hl)
        lay.addSpacing(10)
        grid = QHBoxLayout()
        grid.setSpacing(14)
        self.card_cs2, self.home_cs2_quick = self._discipline_card(
            "🔫", "CS2", "Steam-обзор, FACEIT ELO, история ММ и Премьера.", "cs2")
        self.card_dota, self.home_dota_quick = self._discipline_card(
            "🛡", "Dota 2", "OpenDota: винрейт, MMR, герои, последние 20.", "dota")
        self.card_lol, self.home_lol_quick = self._discipline_card(
            "✨", "LoL", "Riot: ранг, LP, KDA, история матчей по Riot ID.", "lol")
        for c in [self.card_cs2, self.card_dota, self.card_lol]:
            grid.addWidget(c, 1)
        lay.addLayout(grid)
        lay.addStretch(1)
        return w

    # CS2
    def _build_cs2(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        top = QHBoxLayout()
        back = QPushButton("← Главная")
        back.clicked.connect(lambda: self.goto("home"))
        self.cs_profile = QLabel("—")
        self.cs_profile.setStyleSheet("color:#f0a500; font-weight:bold;")
        self.cs_profile.setWordWrap(True)
        top.addWidget(back)
        top.addWidget(self.cs_profile, 1)
        lay.addLayout(top)

        self.cs_tabs = QTabWidget()
        lay.addWidget(self.cs_tabs, 1)

        # Обзор Steam
        t1 = QWidget()
        l1 = QVBoxLayout(t1)
        grid = QGridLayout()
        self.cs_cards = [StatCard(t) for t in ["K/D", "HS %", "Точность", "Винрейт", "Часов", "ADR", "Киллы", "Смерти", "MVP"]]
        for i, c in enumerate(self.cs_cards):
            grid.addWidget(c, i // 3, i % 3)
        l1.addLayout(grid)
        self.cs_rank = RankLine("Линия винрейта (Steam матчи)")
        l1.addWidget(self.cs_rank)
        self.cs_table = make_table(["Игра", "Всего, ч", "2 недели, ч", "AppID"])
        l1.addWidget(QLabel("История по играм (Steam):"))
        l1.addWidget(self.cs_table, 1)
        self.cs_tabs.addTab(t1, "Обзор")

        # FACEIT
        t2 = QWidget()
        l2 = QVBoxLayout(t2)
        self.fc_profile = QLabel("FACEIT: —")
        self.fc_profile.setStyleSheet("color:#f0a500; font-weight:bold;")
        l2.addWidget(self.fc_profile)
        grid2 = QGridLayout()
        self.fc_cards = [StatCard(t) for t in ["ELO", "Уровень", "K/D", "HS %", "Винрейт", "Матчей"]]
        for i, c in enumerate(self.fc_cards):
            grid2.addWidget(c, i // 3, i % 3)
        l2.addLayout(grid2)
        self.fc_rank = RankLine("Линия ELO (FACEIT)")
        l2.addWidget(self.fc_rank)
        self.fc_table = make_table(["Турнир", "Тип", "Счёт", "W/L", "Дата"])
        l2.addWidget(QLabel("Последние 20 FACEIT-матчей:"))
        l2.addWidget(self.fc_table, 1)
        self.cs_tabs.addTab(t2, "FACEIT")

        # ММ / Премьер
        t3 = QWidget()
        l3 = QVBoxLayout(t3)
        info = QLabel(
            "Твой скрин — это gcpd-страница Steam (Premier Ancient 9:13, ты 28-6-16, 50% HS). "
            "У неё НЕТ публичного API — Steam отдаёт её только залогиненному браузеру.")
        info.setWordWrap(True)
        info.setStyleSheet("color:#9aa0b4;")
        l3.addWidget(info)
        row = QHBoxLayout()
        self.gcpd_tab_sel = QComboBox()
        self.gcpd_tab_sel.addItems(["premier", "competitive", "wingman"])
        b_open = QPushButton("Открыть в браузере")
        b_open.clicked.connect(self.open_gcpd_in_browser)
        b_try = QPushButton("Попробовать скачать")
        b_try.clicked.connect(self.try_gcpd)
        row.addWidget(QLabel("Режим:"))
        row.addWidget(self.gcpd_tab_sel, 1)
        row.addWidget(b_open)
        row.addWidget(b_try)
        l3.addLayout(row)
        self.gcpd_out = QLabel("Cookie steamLoginSecure не вставлен — пока пользуйся FACEIT + Обзором. Инструкция в Настройках.")
        self.gcpd_out.setWordWrap(True)
        l3.addWidget(self.gcpd_out)
        self.gcpd_table = make_table(["Что", "Значение"])
        l3.addWidget(self.gcpd_table, 1)
        self.cs_tabs.addTab(t3, "ММ / Премьер")
        return w

    def open_gcpd_in_browser(self):
        from src.utils.helpers import parse_steam_input
        p = parse_steam_input(self.steam_input.text().strip() or self.cfg.get("steam_input", ""))
        if not p["value"]:
            self.status.setText("Сначала введи Steam vanity или ссылку на профиль.")
            return
        # gcpd открывается и по /id/, и по /profiles/
        kind = "id" if p["type"] == "vanity" else "profiles"
        tab = steam_gcpd.TABS.get(self.gcpd_tab_sel.currentText(), "matchhistorypremier")
        webbrowser.open(f"https://steamcommunity.com/{kind}/{p['value']}/gcpd/730/?tab={tab}")

    def try_gcpd(self):
        from src.utils.helpers import parse_steam_input
        p = parse_steam_input(self.steam_input.text().strip() or self.cfg.get("steam_input", ""))
        vanity = p["value"]
        if not vanity:
            self.gcpd_out.setText("Сначала введи Steam vanity сверху.")
            return
        cookie = (self.cfg.get("steam_cookie", "") or "").strip()
        cookies = {"steamLoginSecure": cookie} if cookie else {}
        res = steam_gcpd.fetch_tab(vanity, self.gcpd_tab_sel.currentText(), cookies)
        if res.get("need_login") or "Match Results" not in (res.get("html") or ""):
            self.gcpd_out.setText("Нужен логин (Steam вернул страницу входа).\n\n" + steam_gcpd.COOKIE_HELP + f"\n\nURL: {res.get('url')}")
            self.gcpd_table.setRowCount(0)
            return
        chunks = steam_gcpd.parse_summary_from_html(res.get("html", ""))
        self.gcpd_out.setText(f"Скачано: {res.get('url')} (статус {res.get('status')}). Разбор сырой — полный парсинг таблицы следующим шагом.")
        self.gcpd_table.setRowCount(len(chunks))
        for i, ch in enumerate(chunks):
            self.gcpd_table.setItem(i, 0, QTableWidgetItem(f"chunk {i}"))
            self.gcpd_table.setItem(i, 1, QTableWidgetItem(ch[:300]))

    # DOTA
    def _build_dota(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        top = QHBoxLayout()
        back = QPushButton("← Главная")
        back.clicked.connect(lambda: self.goto("home"))
        self.dota_profile = QLabel("—")
        self.dota_profile.setStyleSheet("color:#f0a500; font-weight:bold;")
        top.addWidget(back)
        top.addWidget(self.dota_profile, 1)
        lay.addLayout(top)
        grid = QGridLayout()
        self.dota_cards = [StatCard(t) for t in ["MMR (est)", "Винрейт", "Побед", "Поражений", "Всего"]]
        for i, c in enumerate(self.dota_cards):
            grid.addWidget(c, 0, i)
        lay.addLayout(grid)
        self.dota_rank = RankLine("Линия винрейта (Dota)")
        lay.addWidget(self.dota_rank)
        self.dota_table = make_table(["Герой id", "K/D/A", "W/L", "Режим", "Длит."])
        lay.addWidget(QLabel("Матчи подробно (последние 20):"))
        lay.addWidget(self.dota_table, 1)
        return w

    # LOL
    def _build_lol(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        top = QHBoxLayout()
        back = QPushButton("← Главная")
        back.clicked.connect(lambda: self.goto("home"))
        self.lol_profile = QLabel("—")
        self.lol_profile.setStyleSheet("color:#f0a500; font-weight:bold;")
        top.addWidget(back)
        top.addWidget(self.lol_profile, 1)
        lay.addLayout(top)
        grid = QGridLayout()
        self.lol_cards = [StatCard(t) for t in ["Ранг", "Винрейт", "KDA", "K / D / A", "Матчей"]]
        for i, c in enumerate(self.lol_cards):
            grid.addWidget(c, 0, i)
        lay.addLayout(grid)
        self.lol_rank = RankLine("Линия ранга (LP)")
        lay.addWidget(self.lol_rank)
        self.lol_table = make_table(["Match ID", "Чемпион", "K/D/A", "W/L", "Длит."])
        lay.addWidget(QLabel("Матчи подробно (последние 12):"))
        lay.addWidget(self.lol_table, 1)
        return w

    # НАСТРОЙКИ
    def _build_settings(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        self.e_steam_key = QLineEdit(self.cfg.get("steam_api_key", ""))
        self.e_faceit_key = QLineEdit(self.cfg.get("faceit_api_key", ""))
        self.e_faceit_nick = QLineEdit(self.cfg.get("faceit_nickname", ""))
        self.e_dota = QLineEdit(str(self.cfg.get("dota_account_id", "")))
        self.e_riot_key = QLineEdit(self.cfg.get("riot_api_key", ""))
        self.e_riot_id = QLineEdit(self.cfg.get("riot_id", ""))
        self.e_cookie = QLineEdit(self.cfg.get("steam_cookie", ""))
        self.e_cookie.setPlaceholderText("steamLoginSecure (для ММ/Премьер истории)")
        # ключи и куку не светим на экране
        for ed in (self.e_steam_key, self.e_faceit_key, self.e_riot_key, self.e_cookie):
            ed.setEchoMode(QLineEdit.Password)
        self.e_routing = QComboBox()
        self.e_routing.addItems(["europe", "asia", "americas"])
        self.e_routing.setCurrentText(self.cfg.get("riot_routing", "europe"))
        self.e_platform = QComboBox()
        self.e_platform.addItems(["euw1", "kr", "ru", "na1", "eun1"])
        self.e_platform.setCurrentText(self.cfg.get("riot_platform", "euw1"))
        self.cb_cs2 = QCheckBox("Показывать CS2 на главной")
        self.cb_dota = QCheckBox("Показывать Dota 2 на главной")
        self.cb_lol = QCheckBox("Показывать LoL на главной")
        self.cb_cs2.setChecked(bool(self.cfg.get("show_cs2", True)))
        self.cb_dota.setChecked(bool(self.cfg.get("show_dota", True)))
        self.cb_lol.setChecked(bool(self.cfg.get("show_lol", True)))
        for label, ed in [
            ("Steam API key:", self.e_steam_key),
            ("FACEIT nickname:", self.e_faceit_nick),
            ("FACEIT API key:", self.e_faceit_key),
            ("Dota account_id:", self.e_dota),
            ("Riot ID (имя#тег):", self.e_riot_id),
            ("Riot API key (RGAPI-...):", self.e_riot_key),
            ("Steam cookie steamLoginSecure (ММ/Премьер):", self.e_cookie),
        ]:
            lay.addWidget(QLabel(label))
            lay.addWidget(ed)
        lay.addWidget(QLabel("Riot routing:"))
        lay.addWidget(self.e_routing)
        lay.addWidget(QLabel("Riot platform:"))
        lay.addWidget(self.e_platform)
        lay.addWidget(self.cb_cs2)
        lay.addWidget(self.cb_dota)
        lay.addWidget(self.cb_lol)
        b = QPushButton("Сохранить настройки")
        b.clicked.connect(self.save_from_ui)
        lay.addWidget(b)
        hint = QLabel(
            "• Steam: вводи vanity из ссылки профиля (после /id/), не логин — с логином API даёт 400.\n"
            "• ММ/Премьер без cookie не скачается — инструкция во вкладке CS2 -> ММ/Премьер.\n"
            "• LoL без Riot-ключа покажет 'нет ключа' — это нормально, ключ живёт 24ч.\n"
            "• Dota: account_id = SteamID64 - 76561197960265728. 404 = профиль скрыт или матчей нет.\n"
            "• Ключи и cookie лежат только локально в config/settings.json (он в .gitignore)."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color:#9aa0b4;")
        lay.addWidget(hint)
        lay.addStretch(1)
        return w

    def save_from_ui(self):
        self.cfg.update({
            "steam_api_key": self.e_steam_key.text().strip(),
            "steam_input": self.steam_input.text().strip(),
            "faceit_api_key": self.e_faceit_key.text().strip(),
            "faceit_nickname": self.e_faceit_nick.text().strip(),
            "dota_account_id": self.e_dota.text().strip(),
            "riot_api_key": self.e_riot_key.text().strip(),
            "riot_id": self.e_riot_id.text().strip(),
            "riot_routing": self.e_routing.currentText(),
            "riot_platform": self.e_platform.currentText(),
            "steam_cookie": self.e_cookie.text().strip(),
            "show_cs2": self.cb_cs2.isChecked(),
            "show_dota": self.cb_dota.isChecked(),
            "show_lol": self.cb_lol.isChecked(),
        })
        save_settings(self.cfg)
        self.apply_visibility()
        QMessageBox.information(self, "StatHub", "Настройки сохранены.")

    def save_silent(self):
        try:
            self.cfg.update({
                "steam_api_key": self.e_steam_key.text().strip(),
                "steam_input": self.steam_input.text().strip(),
                "faceit_api_key": self.e_faceit_key.text().strip(),
                "faceit_nickname": self.e_faceit_nick.text().strip(),
                "dota_account_id": self.e_dota.text().strip(),
                "riot_api_key": self.e_riot_key.text().strip(),
                "riot_id": self.e_riot_id.text().strip(),
                "riot_routing": self.e_routing.currentText(),
                "riot_platform": self.e_platform.currentText(),
                "steam_cookie": self.e_cookie.text().strip(),
                "show_cs2": self.cb_cs2.isChecked(),
                "show_dota": self.cb_dota.isChecked(),
                "show_lol": self.cb_lol.isChecked(),
            })
            save_settings(self.cfg)
            self.apply_visibility()
        except Exception:
            pass

    # ЗАГРУЗКА
    def set_status(self, ok="", err=""):
        self.status.setText(err or ok)
        self.status.setStyleSheet(f"color:{'#ff6b6b' if err else '#7bed9f'};")

    def refresh_all(self):
        self.save_silent()
        errors = []
        if self.cfg.get("show_cs2", True):
            for fn, name in [(self.load_cs2, "CS2"), (self.load_faceit, "FACEIT")]:
                try:
                    fn()
                except Exception as e:
                    errors.append(f"{name}: {e}")
        if self.cfg.get("show_dota", True):
            try:
                self.load_dota()
            except Exception as e:
                errors.append(f"Dota: {e}")
                self.home_dota_quick.setText(f"Ошибка: {e}")
        if self.cfg.get("show_lol", True):
            try:
                self.load_lol()
            except Exception as e:
                # load_lol сам показывает "нет ключа", это не ошибка
                pass
        if errors:
            self.set_status(err=" | ".join(errors))

    # CS2 Steam
    def load_cs2(self):
        key = self.cfg.get("steam_api_key", "")
        raw = self.steam_input.text().strip() or self.cfg.get("steam_input", "")
        sid = steam_api.resolve_steam_id(raw, key)
        self.cfg["steam_id64"] = sid
        try:
            self.cfg["dota_account_id"] = str(steam64_to_account_id(sid))
            self.e_dota.setText(str(self.cfg["dota_account_id"]))
        except Exception:
            pass
        save_settings(self.cfg)
        prof = steam_api.get_player_summary(sid, key)
        stats = steam_api.get_cs2_stats(sid, key)
        d = calc_cs_derived(stats)
        self.cs_profile.setText(f"{prof.get('personaname','—')} • {sid}")
        for c, v in zip(self.cs_cards, [d["kd"], f"{d['hs_percent']}%", f"{d['accuracy']}%",
                                        f"{d['winrate']}%", d["hours"], d["adr"],
                                        d["kills"], d["deaths"], stats.get("total_mvps", "—")]):
            c.set(str(v))
        self.cs_rank.set(f"Винрейт {d['winrate']}% ({stats.get('total_matches_won',0)}/{stats.get('total_matches_played',0)})",
                         d["winrate"],
                         f"Последний матч: {stats.get('last_match_kills',0)}-{stats.get('last_match_deaths',0)}, MVP {stats.get('last_match_mvps',0)}. Любимое: AK-47 {stats.get('total_kills_ak47',0)} / AWP {stats.get('total_kills_awp',0)}.")
        games = steam_api.get_recently_played(sid, key)
        self.cs_table.setRowCount(len(games))
        for i, g in enumerate(games):
            self.cs_table.setItem(i, 0, QTableWidgetItem(g.get("name", "")))
            self.cs_table.setItem(i, 1, QTableWidgetItem(str(round(g.get("playtime_forever", 0) / 60, 1))))
            self.cs_table.setItem(i, 2, QTableWidgetItem(str(round(g.get("playtime_2weeks", 0) / 60, 1))))
            self.cs_table.setItem(i, 3, QTableWidgetItem(str(g.get("appid", ""))))
        self.home_cs2_quick.setText(f"K/D {d['kd']} • HS {d['hs_percent']}% • Винрейт {d['winrate']}% • {d['hours']} ч")
        self.set_status(ok=f"CS2 OK: K/D {d['kd']}, HS {d['hs_percent']}%. 400 нет.")

    def load_faceit(self):
        token = self.cfg.get("faceit_api_key", "")
        nick = self.cfg.get("faceit_nickname", "") 
        try:
            p = faceit_api.search_player(nick, token)
        except RuntimeError:
            self.fc_profile.setText("FACEIT: вставь ключ в Настройках (developers.faceit.com)")
            for c in self.fc_cards:
                c.set("—")
            self.fc_rank.set("ELO неизвестен (нет ключа)", 0, "Steam даёт только суммарную стату. ELO и историю 20 матчей даёт только FACEIT.")
            self.fc_table.setRowCount(0)
            return
        pid = p.get("player_id")
        elo = (p.get("games") or {}).get("cs2", {}).get("faceit_elo", "—")
        lvl = (p.get("games") or {}).get("cs2", {}).get("skill_level", "—")
        self.fc_profile.setText(f"{p.get('nickname','')} • ELO {elo} • lvl {lvl}")
        life = faceit_api.lifetime_cs2(pid, token)
        s = faceit_api.parse_lifetime(life)
        for c, v in zip(self.fc_cards, [elo, lvl, s.get("K/D Ratio", "—"),
                                        f"{s.get('Average Headshots %','—')}%",
                                        f"{s.get('Win Rate %','—')}%", s.get("Matches", "—")]):
            c.set(str(v))
        try:
            self.fc_rank.set(f"ELO {elo} (lvl {lvl})", min(100, int(elo) / 50) if str(elo).isdigit() else 0,
                             f"K/D {s.get('K/D Ratio','—')}, HS {s.get('Average Headshots %','—')}%, матчей {s.get('Matches','—')}")
        except Exception:
            pass
        hist = faceit_api.match_history(pid, token, 20)
        self.fc_table.setRowCount(len(hist))
        for i, m in enumerate(hist):
            res = m.get("results", {})
            self.fc_table.setItem(i, 0, QTableWidgetItem(str(m.get("competition_name", ""))[:30]))
            self.fc_table.setItem(i, 1, QTableWidgetItem(str(m.get("competition_type", ""))))
            self.fc_table.setItem(i, 2, QTableWidgetItem(str((res.get("score") or ""))))
            self.fc_table.setItem(i, 3, QTableWidgetItem("W" if str(res.get("winner")) == pid else "L"))
            self.fc_table.setItem(i, 4, QTableWidgetItem(str(m.get("started_at", ""))[:10]))

    # Dota
    def load_dota(self):
        acc = (self.cfg.get("dota_account_id", "") or "").strip()
        if not acc.isdigit():
            raise RuntimeError("Dota account_id должен быть числом.")
        prof = dota_api.get_profile(acc)
        wl = dota_api.get_wl(acc)
        s = dota_api.summarise(prof, wl)
        self.dota_profile.setText(f"{s['name']} • id {acc}")
        for c, v in zip(self.dota_cards, [s["mmr"], f"{s['winrate']}%", s["wins"], s["losses"], s["total"]]):
            c.set(str(v))
        self.dota_rank.set(f"Винрейт {s['winrate']}%", s["winrate"], f"Побед {s['wins']} / поражений {s['losses']}.")
        self.home_dota_quick.setText(f"Винрейт {s['winrate']}% • {s['wins']}W/{s['losses']}L • MMR ~{s['mmr']}")
        rec = dota_api.get_recent(acc, 20)
        self.dota_table.setRowCount(len(rec))
        for i, m in enumerate(rec):
            self.dota_table.setItem(i, 0, QTableWidgetItem(str(m.get("hero_id", ""))))
            self.dota_table.setItem(i, 1, QTableWidgetItem(f"{m.get('kills')}/{m.get('deaths')}/{m.get('assists')}"))
            win = (m.get("player_slot", 0) < 128) == bool(m.get("radiant_win"))
            self.dota_table.setItem(i, 2, QTableWidgetItem("W" if win else "L"))
            self.dota_table.setItem(i, 3, QTableWidgetItem(str(m.get("game_mode", ""))))
            self.dota_table.setItem(i, 4, QTableWidgetItem(str(round((m.get("duration") or 0) / 60)) + " мин"))

    # LoL
    def load_lol(self):
        key = self.cfg.get("riot_api_key", "")
        rid = self.cfg.get("riot_id", "")
        routing = self.cfg.get("riot_routing", "europe")
        platform = self.cfg.get("riot_platform", "euw1")
        if not key or len(key) < 10:
            self.lol_profile.setText("LoL: вставь Riot API ключ в Настройках (developer.riotgames.com, живёт 24ч)")
            for c in self.lol_cards:
                c.set("—")
            self.lol_rank.set("Ранг неизвестен (нет ключа)", 0, f"Riot ID {rid} введён. Без ключа историю не скачать — ключ бесплатный на 24ч.")
            self.home_lol_quick.setText(f"{rid} • нужен Riot API ключ (см. Настройки).")
            self.lol_table.setRowCount(0)
            return
        name, tag = riot_api.split_riot_id(rid)
        acc = riot_api.get_account(name, tag, routing, key)
        puuid = acc.get("puuid")
        self.lol_profile.setText(f"{acc.get('gameName')}#{acc.get('tagLine')}")
        ids = riot_api.get_match_ids(puuid, routing, key, 12)
        matches = [riot_api.get_match(mid, routing, key) for mid in ids[:12]]
        sm = riot_api.summarise_matches(matches, puuid)
        rank_txt, lp_pct, rank_info = "Unranked", 0, "Нет соло-ранга."
        try:
            summ = riot_api.get_summoner_by_puuid(puuid, platform, key)
            entries = riot_api.get_rank(summ.get("id", ""), platform, key) if summ.get("id") else []
            solo = next((e for e in entries if e.get("queueType") == "RANKED_SOLO_5x5"), entries[0] if entries else None)
            if solo:
                rank_txt = f"{solo.get('tier','')} {solo.get('rank','')}"
                lp = int(solo.get("leaguePoints", 0))
                lp_pct = min(100, lp)
                w, l = solo.get("wins", 0), solo.get("losses", 0)
                rank_info = f"{lp} LP • {w}W/{l}L • винрейт {round(w/max(w+l,1)*100,1)}%."
        except Exception as e:
            rank_info = f"Ранг не прочитан: {e}"
        for c, v in zip(self.lol_cards, [rank_txt, f"{sm.get('winrate','—')}%" if sm.get("matches") else "—",
                                         sm.get("kda", "—"),
                                         f"{sm.get('avg_kills','—')} / {sm.get('avg_deaths','—')} / {sm.get('avg_assists','—')}",
                                         sm.get("matches", "—")]):
            c.set(str(v))
        self.lol_rank.set(f"{rank_txt} — {rank_info}", lp_pct, f"Последние {sm.get('matches',0)}: KDA {sm.get('kda','—')}, винрейт {sm.get('winrate','—')}%.")
        self.home_lol_quick.setText(f"{rank_txt} • KDA {sm.get('kda','—')} • WR {sm.get('winrate','—')}%")
        self.lol_table.setRowCount(len(matches))
        for i, m in enumerate(matches):
            info = m.get("info", {})
            me = next((x for x in info.get("participants", []) if x.get("puuid") == puuid), {})
            self.lol_table.setItem(i, 0, QTableWidgetItem(str(m.get("metadata", {}).get("matchId", ""))[:14]))
            self.lol_table.setItem(i, 1, QTableWidgetItem(str(me.get("championName", ""))))
            self.lol_table.setItem(i, 2, QTableWidgetItem(f"{me.get('kills',0)}/{me.get('deaths',0)}/{me.get('assists',0)}"))
            self.lol_table.setItem(i, 3, QTableWidgetItem("W" if me.get("win") else "L"))
            self.lol_table.setItem(i, 4, QTableWidgetItem(str(round((info.get("gameDuration") or 0) / 60)) + " мин"))
