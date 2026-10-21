"""Сплэш с рандомным временным логотипом. Потом заменим на твой.
Генерирует QPixmap на лету: градиент + буква + название. Рандом из 3 тем.
"""
import random
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap, QPainter, QLinearGradient, QColor, QFont
from PySide6.QtWidgets import QSplashScreen


THEMES = [
    ((240, 165, 0), (20, 22, 30), "StatHub", "CS2 • DOTA • LOL"),
    ((0, 180, 255), (12, 14, 24), "StatHub", "K/D • HS% • WINRATE"),
    ((150, 80, 255), (16, 16, 26), "SH", "STATHUB v1.0"),
]


def make_logo_pixmap(w: int = 520, h: int = 340) -> QPixmap:
    c1, c2, big, small = random.choice(THEMES)
    pm = QPixmap(w, h)
    pm.fill(QColor(*c2))
    p = QPainter(pm)
    grad = QLinearGradient(0, 0, w, h)
    grad.setColorAt(0, QColor(*c1))
    grad.setColorAt(1, QColor(*c2))
    p.fillRect(0, 0, w, 110, grad)
    p.setPen(QColor("#111111"))
    p.setFont(QFont("Arial", 64, QFont.Bold))
    p.drawText(0, 10, w, 100, Qt.AlignCenter, big)
    p.setPen(QColor("#ffffff"))
    p.setFont(QFont("Arial", 20, QFont.Bold))
    p.drawText(0, 150, w, 60, Qt.AlignCenter, "StatHub")
    p.setFont(QFont("Arial", 13))
    p.setPen(QColor("#9aa0b4"))
    p.drawText(0, 210, w, 40, Qt.AlignCenter, small)
    p.setPen(QColor(*c1))
    p.setFont(QFont("Arial", 11))
    p.drawText(0, 260, w, 40, Qt.AlignCenter, "загрузка статистики...")
    p.end()
    return pm


def show_splash(app) -> QSplashScreen:
    splash = QSplashScreen(make_logo_pixmap())
    splash.show()
    app.processEvents()
    return splash
