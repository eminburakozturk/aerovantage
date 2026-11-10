#!/usr/bin/env python3
"""Re-key near-black/near-white plates out of UI brand PNGs (RGBA alpha)."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

BRAND = Path(__file__).resolve().parents[1] / "frontend" / "public" / "brand"


def strip_dark(im: Image.Image, threshold: int = 28) -> Image.Image:
    rgba = im.convert("RGBA")
    px = rgba.load()
    w, h = rgba.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a == 0:
                continue
            mx, mn = max(r, g, b), min(r, g, b)
            if mx <= threshold:
                px[x, y] = (r, g, b, 0)
            elif mx <= threshold + 12 and (mx - mn) <= 18:
                px[x, y] = (r, g, b, 0)
    bbox = rgba.getbbox()
    return rgba.crop(bbox) if bbox else rgba


def strip_white_plate(im: Image.Image) -> Image.Image:
    rgba = im.convert("RGBA")
    px = rgba.load()
    w, h = rgba.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a > 0 and min(r, g, b) >= 230 and max(r, g, b) >= 245:
                px[x, y] = (r, g, b, 0)
    bbox = rgba.getbbox()
    return rgba.crop(bbox) if bbox else rgba


def opaque_dark_count(im: Image.Image, thr: int = 40) -> int:
    return sum(1 for r, g, b, a in im.convert("RGBA").getdata() if a > 0 and max(r, g, b) < thr)


def main() -> None:
    targets = (
        "logo-mark.png",
        "wordmark.png",
        "primary.png",
        "logo-lockup.png",
        "icon.png",
        "favicon-circle.png",
        "app-icon-dark.png",
    )
    for name in targets:
        path = BRAND / name
        before = Image.open(path).convert("RGBA")
        dark_b = opaque_dark_count(before)
        cleaned = strip_dark(before, 28 if name != "app-icon-dark" else 20)
        if name == "app-icon-dark":
            cleaned = strip_white_plate(cleaned)
        cleaned.save(path)
        after = Image.open(path).convert("RGBA")
        print(
            f"{name}: {before.size}->{after.size} "
            f"dark_opaque {dark_b}->{opaque_dark_count(after)} "
            f"corner={after.getpixel((0, 0))} "
            f"alpha={after.getchannel('A').getextrema()}"
        )

    mark = Image.open(BRAND / "logo-mark.png").convert("RGBA")
    word = Image.open(BRAND / "wordmark.png").convert("RGBA")
    mark_s = mark.copy()
    mark_s.thumbnail((56, 56), Image.Resampling.LANCZOS)
    word_s = word.copy()
    word_s.thumbnail((220, 48), Image.Resampling.LANCZOS)
    h = max(mark_s.height, word_s.height)
    lockup = Image.new("RGBA", (mark_s.width + 12 + word_s.width, h), (0, 0, 0, 0))
    lockup.paste(mark_s, (0, (h - mark_s.height) // 2), mark_s)
    lockup.paste(word_s, (mark_s.width + 12, (h - word_s.height) // 2), word_s)
    lockup.save(BRAND / "logo-lockup.png")
    print("rebuilt logo-lockup", lockup.size, lockup.getpixel((0, 0)))

    # Transparent favicon / icons used in browser chrome shouldn't carry navy plates for mark-like use
    # Keep icon-{size}.png as app icons with soft navy (intentional), but refresh favicon.png transparent.
    canvas = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    fitted = mark.copy()
    fitted.thumbnail((28, 28), Image.Resampling.LANCZOS)
    canvas.paste(fitted, ((32 - fitted.width) // 2, (32 - fitted.height) // 2), fitted)
    canvas.save(BRAND / "favicon.png")
    print("favicon.png refreshed transparent")


if __name__ == "__main__":
    main()
