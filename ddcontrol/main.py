"""Punkt wejścia aplikacji DD Control."""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from PySide6.QtCore import QTimer, QUrl
from PySide6.QtGui import QFont, QGuiApplication, QIcon
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle

from . import __version__
from .backend import Backend
from .storage import Store


def resource_dir() -> Path:
    # PyInstaller rozpakowuje dane do sys._MEIPASS
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    return base / "ddcontrol"


def _screenshot_tour(engine: QQmlApplicationEngine, out_dir: Path, app: QGuiApplication) -> None:
    """Tryb diagnostyczny: zrzut ekranu każdej strony i wyjście."""
    out_dir.mkdir(parents=True, exist_ok=True)
    window = engine.rootObjects()[0]
    names = window.property("pageNames")  # QJSValue z tablicą JS
    pages = names.toVariant() if hasattr(names, "toVariant") else list(names)
    order = list(range(len(pages)))
    window.setProperty("height", 1500)  # cała strona na jednym zrzucie

    def shoot(i: int = 0) -> None:
        if i >= len(order):
            app.quit()
            return
        window.setProperty("currentPage", order[i])
        QTimer.singleShot(1200, lambda: (
            window.grabWindow().save(str(out_dir / f"{order[i]}_{pages[order[i]]}.png")),
            shoot(i + 1)))

    QTimer.singleShot(2500, shoot)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="DD Control - konfigurator bazy FFBeast")
    parser.add_argument("--demo", action="store_true", help="tryb symulacji (bez sprzętu)")
    parser.add_argument("--screenshots", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("-v", "--verbose", action="store_true")
    args, qt_args = parser.parse_known_args(argv)

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    QQuickStyle.setStyle("Basic")
    app = QGuiApplication([sys.argv[0], *qt_args])
    app.setApplicationName("DD Control")
    app.setOrganizationName("DDControl")
    app.setApplicationVersion(__version__)
    font = QFont("Segoe UI")
    font.setPixelSize(13)
    app.setFont(font)
    res = resource_dir()
    app.setWindowIcon(QIcon(str(res / "assets" / "icon.png")))

    backend = Backend(Store(), simulate=True if args.demo else None)
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("backend", backend)
    engine.rootContext().setContextProperty("appVersion", __version__)
    engine.load(QUrl.fromLocalFile(str(res / "qml" / "Main.qml")))
    if not engine.rootObjects():
        return 1

    backend.start()
    app.aboutToQuit.connect(backend.shutdown)
    if args.screenshots:
        _screenshot_tour(engine, args.screenshots, app)
    code = app.exec()
    del engine  # QML znika przed backendem - bez ostrzeżeń przy zamykaniu
    return code


if __name__ == "__main__":
    raise SystemExit(main())
