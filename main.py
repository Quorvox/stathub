import sys
import time
from PySide6.QtWidgets import QApplication
from src.ui.splash import show_splash
from src.ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    splash = show_splash(app)
    splash.showMessage("Загрузка StatHub...", 0)
    # подзагрузка лого
    t0 = time.time()
    w = MainWindow()
    while time.time() - t0 < 1.4:
        app.processEvents()
        time.sleep(0.05)
    w.show()
    splash.finish(w)
    try:
        w.refresh_all()
    except Exception as e:
        print("Autoload:", e)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
