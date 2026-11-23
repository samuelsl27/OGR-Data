from __future__ import annotations

import sys


def main() -> int:
    from PySide6.QtWidgets import QApplication

    from .gui import i18n
    from .gui.main_window import MainWindow
    from .gui.settings import app_settings

    app = QApplication(sys.argv)
    # spec 024: interface language (saved choice; first start follows the system)
    language = i18n.saved_language(app_settings())
    i18n.set_language(language)
    i18n.install_qt_translator(app, language)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
