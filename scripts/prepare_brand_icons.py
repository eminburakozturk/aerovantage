#!/usr/bin/env python3
"""Marka PNG'lerinden Windows .ico ve tray/exe ikonlari uretir."""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
BRAND = ROOT / "frontend" / "public" / "brand"
ASSETS = ROOT / "launcher" / "assets"
SIZES = (16, 24, 32, 48, 64, 128, 256)


def _load_mark() -> Image.Image:
    for name in ("logo-mark.png", "icon-192.png", "icon-64.png"):
        path = BRAND / name
        if path.exists():
            return Image.open(path).convert("RGBA")
    raise FileNotFoundError(f"Brand mark bulunamadi: {BRAND}")


def _fit(mark: Image.Image, size: int, *, pad_ratio: float = 0.1, bg=(0, 0, 0, 0)) -> Image.Image:
    canvas = Image.new("RGBA", (size, size), bg)
    pad = max(1, int(size * pad_ratio))
    fitted = mark.copy()
    fitted.thumbnail((size - pad * 2, size - pad * 2), Image.Resampling.LANCZOS)
    x = (size - fitted.width) // 2
    y = (size - fitted.height) // 2
    canvas.paste(fitted, (x, y), fitted)
    return canvas


def main() -> int:
    ASSETS.mkdir(parents=True, exist_ok=True)
    BRAND.mkdir(parents=True, exist_ok=True)

    mark = _load_mark()
    largest = _fit(mark, 256, pad_ratio=0.08)

    ico_targets = [
        ASSETS / "aerovantage.ico",
        ROOT / "AeroVantage.ico",
        BRAND / "aerovantage.ico",
    ]
    for ico_path in ico_targets:
        largest.save(
            ico_path,
            format="ICO",
            sizes=[(s, s) for s in SIZES],
        )
        print(f"[brand] ICO: {ico_path}")

    tray = _fit(mark, 64, pad_ratio=0.08)
    tray.save(ASSETS / "tray-64.png")
    tray.save(BRAND / "icon-64.png")
    print(f"[brand] Tray PNG: {ASSETS / 'tray-64.png'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
