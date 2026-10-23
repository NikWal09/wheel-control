"""Renderuje rzut kierownicy z modelu STL (assets/wheel_front.png) i wypisuje pozycje przycisków.

    python tools/render_wheel.py base.stl

Widok od strony kierowcy (+Z, oś Y w górę). Wymaga numpy. Pozycje otworów na przyciski
(Ø12 mm) wypisuje w jednostkach WheelGraphic.qml (2 jednostki = 1 mm, początek w lewym górnym
rogu obrazu), w kolejności U: lewa góra -> w dół -> prawa strona w górę.
"""
import sys
from collections import deque
from pathlib import Path

import numpy as np
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QGuiApplication, QImage, QPainter, QPolygonF

MARGIN_MM = 2.0
UNITS_PER_MM = 2         # układ współrzędnych WheelGraphic.qml
PX_PER_MM = 4            # rozdzielczość obrazu
SUPERSAMPLE = 2
PLATE_Z = 28.0           # płyta czołowa leży na Z ~ 29.6 mm; niżej = otwory
BUTTON_HOLE_MM = (10.0, 14.0)
LIGHT = np.array([-0.45, 0.55, 1.0]) / np.linalg.norm([-0.45, 0.55, 1.0])
BASE = np.array([46, 50, 58], dtype=float)  # grafit


def load_stl(path: str) -> np.ndarray:
    data = np.fromfile(path, dtype=np.uint8)
    n = int(np.frombuffer(data[80:84].tobytes(), dtype=np.uint32)[0])
    rec = np.dtype([("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")])
    return np.frombuffer(data[84:84 + n * 50].tobytes(), dtype=rec)["v"].astype(np.float64)


def render(v: np.ndarray, lo: np.ndarray, hi: np.ndarray, out: Path) -> None:
    px = PX_PER_MM * SUPERSAMPLE
    w = int(round((hi[0] - lo[0] + 2 * MARGIN_MM) * px))
    h = int(round((hi[1] - lo[1] + 2 * MARGIN_MM) * px))
    img = QImage(w, h, QImage.Format_ARGB32_Premultiplied)
    img.fill(Qt.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing, False)

    n = np.cross(v[:, 1] - v[:, 0], v[:, 2] - v[:, 0])
    n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
    n[n[:, 2] < 0] *= -1                                   # patrzymy od +Z
    diffuse = np.clip(n @ LIGHT, 0, 1)
    spec = np.clip(n @ (LIGHT + [0, 0, 1]) / np.linalg.norm(LIGHT + [0, 0, 1]), 0, 1) ** 24
    zmean = v[:, :, 2].mean(1)
    depth = np.clip((zmean - lo[2]) / (PLATE_Z - lo[2]), 0, 1) ** 2  # wnętrze otworów ciemne
    shade = (0.30 + 0.70 * diffuse) * (0.15 + 0.85 * depth)
    for i in np.argsort(zmean):
        c = np.clip(BASE * shade[i] * 1.3 + 110 * spec[i] * depth[i], 0, 255).astype(int)
        color = QColor(int(c[0]), int(c[1]), int(c[2]))
        p.setPen(color)
        p.setBrush(color)
        t = v[i]
        p.drawPolygon(QPolygonF([QPointF((t[k][0] - lo[0] + MARGIN_MM) * px, (hi[1] - t[k][1] + MARGIN_MM) * px)
                                 for k in range(3)]))
    p.end()
    img = img.scaled(w // SUPERSAMPLE, h // SUPERSAMPLE, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
    img.save(str(out))
    print(f"zapisano {out} ({img.width()}x{img.height()})")


def button_holes(v: np.ndarray, lo: np.ndarray, hi: np.ndarray) -> list[tuple[float, float]]:
    """Środki okrągłych otworów Ø~12 mm w płycie czołowej (mm, układ modelu)."""
    px = 3.0
    w = int((hi[0] - lo[0]) * px) + 8
    h = int((hi[1] - lo[1]) * px) + 8
    img = QImage(w, h, QImage.Format_RGB32)
    img.fill(QColor(0, 0, 0))
    p = QPainter(img)
    white = QColor(255, 255, 255)
    p.setPen(white)
    p.setBrush(white)
    for t in v[v[:, :, 2].max(1) > PLATE_Z]:
        p.drawPolygon(QPolygonF([QPointF(4 + (t[k][0] - lo[0]) * px, h - 4 - (t[k][1] - lo[1]) * px)
                                 for k in range(3)]))
    p.end()
    buf = np.frombuffer(img.constBits(), dtype=np.uint32).reshape(h, img.bytesPerLine() // 4)[:, :w]
    solid = (buf & 0xFF) > 0
    seen = np.zeros_like(solid)
    holes = []
    for sy, sx in zip(*np.nonzero(~solid)):
        if seen[sy, sx]:
            continue
        q, pts, border = deque([(sy, sx)]), [], False
        seen[sy, sx] = True
        while q:
            y, x = q.popleft()
            pts.append((y, x))
            border |= y in (0, h - 1) or x in (0, w - 1)
            for ny, nx in ((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)):
                if 0 <= ny < h and 0 <= nx < w and not solid[ny, nx] and not seen[ny, nx]:
                    seen[ny, nx] = True
                    q.append((ny, nx))
        d = 2 * np.sqrt(len(pts) / px ** 2 / np.pi)
        if not border and BUTTON_HOLE_MM[0] <= d <= BUTTON_HOLE_MM[1]:
            a = np.array(pts, dtype=float)
            holes.append(((a[:, 1].mean() - 4) / px + lo[0], (h - 4 - a[:, 0].mean()) / px + lo[1]))
    left = sorted([c for c in holes if c[0] < 0], key=lambda c: (-c[1]))
    right = sorted([c for c in holes if c[0] >= 0], key=lambda c: (c[1]))
    return left + right


def main() -> None:
    app = QGuiApplication.instance() or QGuiApplication(sys.argv)  # noqa: F841 - QPainter potrzebuje aplikacji
    v = load_stl(sys.argv[1])
    lo, hi = v.reshape(-1, 3).min(0), v.reshape(-1, 3).max(0)
    out = Path(__file__).resolve().parent.parent / "ddcontrol" / "assets" / "wheel_front.png"
    render(v, lo, hi, out)
    size = ((hi[0] - lo[0] + 2 * MARGIN_MM) * UNITS_PER_MM, (hi[1] - lo[1] + 2 * MARGIN_MM) * UNITS_PER_MM)
    print(f"rozmiar w WheelGraphic: {size[0]:.0f} x {size[1]:.0f}")
    holes = button_holes(v, lo, hi)
    units = [((x - lo[0] + MARGIN_MM) * UNITS_PER_MM, (hi[1] - y + MARGIN_MM) * UNITS_PER_MM) for x, y in holes]
    print(f"{len(units)} przycisków (kolejność U):")
    print("[" + ", ".join(f"[{x:.0f}, {y:.0f}]" for x, y in units) + "]")


if __name__ == "__main__":
    main()
