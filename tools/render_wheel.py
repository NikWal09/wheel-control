"""Renderuje rzut kierownicy z modelu STL (assets/wheel_front.png) i wypisuje pozycje elementów.

    python tools/render_wheel.py base.stl

Widok od strony kierowcy (+Z, oś Y w górę), wygląd jak prawdziwa kierownica: płyta z karbonu,
matowe czarne uchwyty (druk 3D), srebrne śruby piasty, moduł diod na dole. Okna na dłonie są
przezroczyste - łopatki rysuje WheelGraphic.qml pod obrazem. Wymaga numpy.

Pozycje wypisuje w jednostkach WheelGraphic.qml (2 jednostki = 1 mm, początek w lewym górnym rogu
obrazu): otwory przycisków Ø12 mm (lewa kolumna od góry, potem prawa od góry) i diody.
"""
import sys
from collections import deque
from pathlib import Path

import numpy as np
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (QColor, QGuiApplication, QImage, QPainter, QPainterPath, QPen, QPolygonF,
                           QRadialGradient, QLinearGradient)

MARGIN_MM = 2.0
UNITS_PER_MM = 2          # układ współrzędnych WheelGraphic.qml
PX_PER_MM = 4             # rozdzielczość obrazu
SUPERSAMPLE = 2
PLATE_TOP = 29.65         # górna powierzchnia płyty czołowej
SEE_THROUGH_Z = 27.0      # niżej niż spód płyty = przez otwór widać to, co za kierownicą
BUTTON_HOLE_MM = (10.0, 14.0)
LIGHT = np.array([-0.45, 0.6, 1.0]) / np.linalg.norm([-0.45, 0.6, 1.0])

# elementy, których nie ma w modelu (ze zdjęcia i rysunku CAD), w mm układu modelu
HUB_SCREWS = [(-30.3, 17.6), (30.2, 17.6), (-30.3, -17.4), (30.2, -17.4), (0.0, 35.1), (0.0, -34.9)]
SMALL_SCREWS = [(-86.2, 62.0), (86.1, 62.0), (-52.2, -38.9), (51.9, -38.9)]
LED_HOUSING = [(-21.3, -56.0), (21.3, -56.0), (60.8, -72.3), (-60.8, -72.3)]
LEDS = [(-12.5, -64.7), (0.0, -64.7), (12.5, -64.7)]
LED_D = 6.2


def load_stl(path: str) -> np.ndarray:
    data = np.fromfile(path, dtype=np.uint8)
    n = int(np.frombuffer(data[80:84].tobytes(), dtype=np.uint32)[0])
    rec = np.dtype([("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")])
    return np.frombuffer(data[84:84 + n * 50].tobytes(), dtype=rec)["v"].astype(np.float64)


def rasterize(v, colors, lo, hi, px):
    """Rysuje trójkąty od najniższego (metoda malarza) - zostaje kolor najwyższej powierzchni."""
    w = int(round((hi[0] - lo[0] + 2 * MARGIN_MM) * px))
    h = int(round((hi[1] - lo[1] + 2 * MARGIN_MM) * px))
    img = QImage(w, h, QImage.Format_RGB32)
    img.fill(QColor(0, 0, 0))
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing, False)
    for i in np.argsort(v[:, :, 2].mean(1)):
        c = QColor(int(colors[i, 0]), int(colors[i, 1]), int(colors[i, 2]))
        p.setPen(c)
        p.setBrush(c)
        t = v[i]
        p.drawPolygon(QPolygonF([QPointF((t[k][0] - lo[0] + MARGIN_MM) * px, (hi[1] - t[k][1] + MARGIN_MM) * px)
                                 for k in range(3)]))
    p.end()
    buf = np.frombuffer(img.constBits(), dtype=np.uint32).reshape(h, img.bytesPerLine() // 4)[:, :w]
    return buf.copy()


def carbon(xmm, ymm):
    """Splot skośny 2x2 (twill) jak na płycie: jasność 0..1."""
    tow = 2.6
    u, v = (xmm + ymm) / tow, (xmm - ymm) / tow
    i, j = np.floor(u), np.floor(v)
    along_u = ((i + 2 * j) % 4) < 2
    fu, fv = u - i, v - j
    across = np.where(along_u, fv, fu)
    along = np.where(along_u, fu, fv)
    tow_shape = np.sin(np.pi * across) ** 0.6           # zaokrąglony przekrój wiązki
    sheen = 0.75 + 0.25 * np.cos(2 * np.pi * along)     # połysk wzdłuż włókna
    return np.where(along_u, 0.55, 0.85) * tow_shape * sheen


def shift(m, dy, dx):
    out = np.zeros_like(m)
    h, w = m.shape
    out[max(dy, 0):h + min(dy, 0), max(dx, 0):w + min(dx, 0)] = m[max(-dy, 0):h + min(-dy, 0),
                                                                   max(-dx, 0):w + min(-dx, 0)]
    return out


def edge(mask, width):
    inner = mask.copy()
    for _ in range(width):
        inner = inner & shift(inner, 1, 0) & shift(inner, -1, 0) & shift(inner, 0, 1) & shift(inner, 0, -1)
    return mask & ~inner


def render(v: np.ndarray, lo: np.ndarray, hi: np.ndarray, out: Path) -> None:
    px = PX_PER_MM * SUPERSAMPLE
    zmean = v[:, :, 2].mean(1)
    zspan = hi[2] - lo[2] + 2
    code = ((zmean - lo[2] + 1) / zspan * 0xFFFFFF).astype(np.int64)
    zbuf = rasterize(v, np.stack([(code >> 16) & 255, (code >> 8) & 255, code & 255], 1), lo, hi, px)
    n = np.cross(v[:, 1] - v[:, 0], v[:, 2] - v[:, 0])
    n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
    n[n[:, 2] < 0] *= -1                                     # patrzymy od +Z
    nbuf = rasterize(v, np.clip((n + 1) * 127.5, 0, 255), lo, hi, px)

    filled = (zbuf & 0xFFFFFF) > 0
    z = np.where(filled, (zbuf & 0xFFFFFF) / 0xFFFFFF * zspan + lo[2] - 1, -1e9)
    nx = ((nbuf >> 16) & 255) / 127.5 - 1
    ny = ((nbuf >> 8) & 255) / 127.5 - 1
    nz = (nbuf & 255) / 127.5 - 1
    h, w = z.shape
    yy, xx = np.mgrid[0:h, 0:w]
    xmm = xx / px - MARGIN_MM + lo[0]
    ymm = hi[1] + MARGIN_MM - yy / px

    solid = z > SEE_THROUGH_Z
    plate = solid & (np.abs(z - PLATE_TOP) < 0.6) & (nz > 0.97)
    grip = solid & ~plate
    diffuse = np.clip(nx * LIGHT[0] + ny * LIGHT[1] + nz * LIGHT[2], 0, 1)
    half = (LIGHT + [0, 0, 1]) / np.linalg.norm(LIGHT + [0, 0, 1])
    spec = np.clip(nx * half[0] + ny * half[1] + nz * half[2], 0, 1)

    rgb = np.zeros((h, w, 3))
    # karbon: splot + szeroki ukośny odblask jak na zdjęciu
    weave = carbon(xmm, ymm)
    gloss = np.exp(-((xmm * 0.55 + ymm - 10) / 45) ** 2)
    plate_l = 30 + 30 * weave + 26 * gloss * (0.4 + 0.6 * weave)
    rgb[plate] = np.stack([plate_l, plate_l + 1, plate_l + 4], -1)[plate]
    # uchwyty: matowy czarny druk, światło od lewej góry, jasna krawędź (fresnel) dla kształtu
    rim = np.clip(1 - nz, 0, 1) ** 1.5
    grip_l = 18 + 34 * diffuse + 40 * spec ** 18 + 38 * rim * (0.5 + 0.5 * diffuse)
    rgb[grip] = np.stack([grip_l, grip_l + 1, grip_l + 3], -1)[grip]
    # krawędzie: cięta krawędź płyty i obrys całości - kierownica odcina się od ciemnego tła
    plate_edge = edge(plate, 2) & ~edge(solid, 2)
    rgb[plate_edge] = rgb[plate_edge] * 0.5 + 62
    outline = edge(solid, 3)
    rgb[outline] = rgb[outline] * 0.45 + 95

    alpha = solid.astype(float)
    rgba = np.concatenate([np.clip(rgb, 0, 255) * alpha[..., None], alpha[..., None] * 255], -1)
    s = SUPERSAMPLE
    rgba = rgba[:h // s * s, :w // s * s].reshape(h // s, s, w // s, s, 4).mean((1, 3))
    data = np.ascontiguousarray(rgba.round().astype(np.uint8))
    img = QImage(data.data, data.shape[1], data.shape[0], data.shape[1] * 4,
                 QImage.Format_RGBA8888_Premultiplied).copy()
    draw_details(img, lo, hi)
    img.save(str(out))
    print(f"zapisano {out} ({img.width()}x{img.height()})")


def draw_details(img: QImage, lo: np.ndarray, hi: np.ndarray) -> None:
    """Śruby, moduł diod - elementy spoza modelu, narysowane w miejscach z rysunku CAD."""
    px = PX_PER_MM

    def pt(x, y):
        return QPointF((x - lo[0] + MARGIN_MM) * px, (hi[1] - y + MARGIN_MM) * px)

    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    # moduł diod: czarny wydruk ze skośną górną ścianką
    poly = QPolygonF([pt(x, y) for x, y in LED_HOUSING])
    g = QLinearGradient(pt(0, -56), pt(0, -72.3))
    g.setColorAt(0, QColor(58, 60, 66))
    g.setColorAt(0.18, QColor(30, 31, 35))
    g.setColorAt(1, QColor(22, 23, 26))
    p.setPen(QPen(QColor(88, 92, 100), 1.6))
    p.setBrush(g)
    p.drawPolygon(poly)
    for x, y in LEDS:
        r = LED_D / 2 * px
        p.setPen(QPen(QColor(70, 73, 80), 1.2))
        p.setBrush(QColor(10, 11, 13))
        p.drawEllipse(pt(x, y), r + 1.5, r + 1.5)
    # srebrne śruby piasty (łeb krzyżakowy z podkładką)
    for x, y in HUB_SCREWS:
        c, r = pt(x, y), 4.4 * px
        rg = QRadialGradient(c + QPointF(-r * 0.35, -r * 0.35), r * 1.4)
        rg.setColorAt(0, QColor(236, 238, 240))
        rg.setColorAt(0.6, QColor(168, 172, 178))
        rg.setColorAt(1, QColor(96, 100, 108))
        p.setPen(QPen(QColor(60, 63, 70), 1.2))
        p.setBrush(rg)
        p.drawEllipse(c, r, r)
        p.setPen(QPen(QColor(70, 74, 82), 2.6, Qt.SolidLine, Qt.RoundCap))
        k = r * 0.45
        p.drawLine(c + QPointF(-k, 0), c + QPointF(k, 0))
        p.drawLine(c + QPointF(0, -k), c + QPointF(0, k))
    # małe czarne śruby imbusowe
    for x, y in SMALL_SCREWS:
        c, r = pt(x, y), 2.7 * px
        rg = QRadialGradient(c + QPointF(-r * 0.3, -r * 0.3), r * 1.3)
        rg.setColorAt(0, QColor(78, 80, 86))
        rg.setColorAt(1, QColor(20, 21, 24))
        p.setPen(QPen(QColor(10, 10, 12), 1))
        p.setBrush(rg)
        p.drawEllipse(c, r, r)
        hexagon = QPainterPath()
        for k in range(7):
            a = np.pi / 3 * k
            q = c + QPointF(np.cos(a) * r * 0.42, np.sin(a) * r * 0.42)
            hexagon.moveTo(q) if k == 0 else hexagon.lineTo(q)
        p.fillPath(hexagon, QColor(8, 8, 10))
    p.end()


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
    for t in v[v[:, :, 2].max(1) > SEE_THROUGH_Z + 1]:
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
    right = sorted([c for c in holes if c[0] >= 0], key=lambda c: (-c[1]))
    return left + right


def main() -> None:
    app = QGuiApplication.instance() or QGuiApplication(sys.argv)  # noqa: F841 - QPainter potrzebuje aplikacji
    v = load_stl(sys.argv[1])
    lo, hi = v.reshape(-1, 3).min(0), v.reshape(-1, 3).max(0)
    out = Path(__file__).resolve().parent.parent / "ddcontrol" / "assets" / "wheel_front.png"
    render(v, lo, hi, out)

    def units(x, y):
        return (x - lo[0] + MARGIN_MM) * UNITS_PER_MM, (hi[1] - y + MARGIN_MM) * UNITS_PER_MM

    size = units(hi[0] + MARGIN_MM, lo[1] - MARGIN_MM)
    print(f"rozmiar w WheelGraphic: {size[0]:.0f} x {size[1]:.0f}")
    holes = button_holes(v, lo, hi)
    print(f"{len(holes)} przycisków (lewa kolumna od góry, prawa od góry):")
    print("[" + ", ".join("[%.0f, %.0f]" % units(x, y) for x, y in holes) + "]")
    print("diody: [" + ", ".join("[%.0f, %.0f]" % units(x, y) for x, y in LEDS) + "]")


if __name__ == "__main__":
    main()
