"""Generuje ikonę aplikacji (assets/icon.png i icon.ico)."""
import sys
from pathlib import Path

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QGuiApplication, QImage, QLinearGradient, QPainter

out = Path(__file__).resolve().parent.parent / "ddcontrol" / "assets"
app = QGuiApplication(sys.argv)
size = 256
img = QImage(size, size, QImage.Format_ARGB32)
img.fill(Qt.transparent)
p = QPainter(img)
p.setRenderHint(QPainter.Antialiasing)
g = QLinearGradient(0, 0, size, size)
g.setColorAt(0, QColor("#FF6A4D"))
g.setColorAt(1, QColor("#B3200A"))
p.setBrush(g)
p.setPen(Qt.NoPen)
p.drawRoundedRect(QRectF(8, 8, size - 16, size - 16), 56, 56)
f = QFont("Bahnschrift")
f.setPixelSize(118)
f.setBold(True)
p.setFont(f)
p.setPen(QColor("white"))
p.drawText(QRectF(0, 0, size, size), Qt.AlignCenter, "DD")
p.end()
img.save(str(out / "icon.png"))
img.save(str(out / "icon.ico"))
print("ok", out)
