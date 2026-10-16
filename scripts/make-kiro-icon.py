#!/usr/bin/env python3
"""Draw the Knowledge Garden power icon (a sprout growing from an open book) as a PNG.

Standard library only, so it runs anywhere the build does:

    python3 scripts/make-kiro-icon.py    # writes scripts/kiro-power-icon.png

scripts/build-kiro-power.py copies the PNG into the power and embeds it in POWER.md.
"""

from __future__ import annotations

import math
import struct
import zlib
from pathlib import Path

SIZE = 512
SS = 4  # supersamples per axis for anti-aliasing
OUT = Path(__file__).resolve().parent / "kiro-power-icon.png"

Color = tuple[int, int, int]
px: list[list[list[float]]] = [[[0.0, 0.0, 0.0, 0.0] for _ in range(SIZE)] for _ in range(SIZE)]


def hexc(h: str) -> Color:
    return int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16)


def paint(inside, bbox, color) -> None:
    """Blend `color` (a Color, or a function of y) over every pixel `inside` covers."""
    x0, y0, x1, y1 = (max(0, int(v)) for v in bbox)
    x1, y1 = min(SIZE, x1 + 1), min(SIZE, y1 + 1)
    offs = [(i + 0.5) / SS for i in range(SS)]
    for y in range(y0, y1):
        c = color(y) if callable(color) else color
        for x in range(x0, x1):
            hits = sum(inside(x + ox, y + oy) for oy in offs for ox in offs)
            if not hits:
                continue
            a = hits / (SS * SS)
            p = px[y][x]
            out_a = a + p[3] * (1 - a)
            for i in range(3):
                p[i] = (c[i] * a + p[i] * p[3] * (1 - a)) / out_a
            p[3] = out_a


def rounded_rect(x0, y0, x1, y1, r):
    def inside(x, y):
        cx, cy = min(max(x, x0 + r), x1 - r), min(max(y, y0 + r), y1 - r)
        return x0 <= x <= x1 and y0 <= y <= y1 and (x - cx) ** 2 + (y - cy) ** 2 <= r * r
    return inside, (x0, y0, x1, y1)


def polygon(pts):
    def inside(x, y):
        n, hit = len(pts), False
        for i in range(n):
            (ax, ay), (bx, by) = pts[i], pts[(i + 1) % n]
            if (ay > y) != (by > y) and x < ax + (y - ay) * (bx - ax) / (by - ay):
                hit = not hit
        return hit
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return inside, (min(xs), min(ys), max(xs), max(ys))


def leaf(cx, cy, length, width, angle_deg):
    """A pointed leaf: the overlap of two circles, rotated to `angle_deg`."""
    a = math.radians(angle_deg)
    half = length / 2
    r = (half * half + width * width) / (2 * width)
    d = r - width

    def inside(x, y):
        dx, dy = x - cx, y - cy
        u = dx * math.cos(a) + dy * math.sin(a)
        v = -dx * math.sin(a) + dy * math.cos(a)
        return u * u + (v - d) ** 2 <= r * r and u * u + (v + d) ** 2 <= r * r
    return inside, (cx - half, cy - half, cx + half, cy + half)


def line(x0, y0, x1, y1, w):
    def inside(x, y):
        vx, vy = x1 - x0, y1 - y0
        t = max(0.0, min(1.0, ((x - x0) * vx + (y - y0) * vy) / (vx * vx + vy * vy)))
        return (x - x0 - t * vx) ** 2 + (y - y0 - t * vy) ** 2 <= (w / 2) ** 2
    return inside, (min(x0, x1) - w, min(y0, y1) - w, max(x0, x1) + w, max(y0, y1) + w)


def gradient(top: str, bottom: str):
    t, b = hexc(top), hexc(bottom)
    return lambda y: tuple(round(t[i] + (b[i] - t[i]) * y / SIZE) for i in range(3))


def draw() -> None:
    paint(*rounded_rect(0, 0, SIZE - 1, SIZE - 1, 112), gradient("#2F8A57", "#174B30"))

    # Open book: a shadow edge, then the two pages meeting at the spine.
    paint(*polygon([(92, 330), (256, 360), (420, 330), (420, 410), (256, 440), (92, 410)]),
          hexc("#C9BC98"))
    paint(*polygon([(92, 316), (252, 346), (252, 424), (92, 394)]), hexc("#FBF6E8"))
    paint(*polygon([(420, 316), (260, 346), (260, 424), (420, 394)]), hexc("#F1E9D2"))
    for i in range(3):  # text lines on each page
        y = 352 + i * 18
        paint(*line(122, y - 18 + i * 2, 220, y + i * 2, 6), hexc("#D8CCAA"))
        paint(*line(292, y + i * 2, 390, y - 18 + i * 2, 6), hexc("#D8CCAA"))

    # Sprout: stem, then two leaves with a midrib.
    paint(*line(256, 344, 256, 196, 16), hexc("#9BD86C"))
    paint(*leaf(196, 226, 132, 46, -150), hexc("#8ACB5A"))
    paint(*line(250, 252, 152, 198, 5), hexc("#5E9E3A"))
    paint(*leaf(320, 168, 150, 52, -30), hexc("#B6EA84"))
    paint(*line(262, 202, 378, 136, 5), hexc("#6FAE45"))


def write_png(path: Path) -> None:
    raw = bytearray()
    for row in px:
        raw.append(0)
        for r, g, b, a in row:
            raw += bytes((round(r), round(g), round(b), round(a * 255)))

    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data))

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", SIZE, SIZE, 8, 6, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += chunk(b"IEND", b"")
    path.write_bytes(png)


if __name__ == "__main__":
    draw()
    write_png(OUT)
    print(f"Wrote {OUT.relative_to(OUT.parent.parent)} ({OUT.stat().st_size // 1024} KB)")
