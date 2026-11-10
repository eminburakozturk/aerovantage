"""Extract AeroVantage logo crops from brand identity sheet (tuned)."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

SRC = Path(
    r"C:\Users\Burak\.cursor\projects\c-Users-Burak-aerovantage\assets"
    r"\c__Users_Burak_AppData_Roaming_Cursor_User_workspaceStorage_empty-window_images_"
    r"cfecbd2c-45bf-4e1b-9274-78b494d5cf81-9f8bb995-4be0-422b-b3f1-27868218ca86.png"
)
OUT = Path(__file__).resolve().parents[1] / "frontend" / "public" / "brand"


def to_transparent(im: Image.Image, threshold: int = 18) -> Image.Image:
    rgba = im.convert("RGBA")
    px = list(rgba.getdata())
    out = []
    for r, g, b, a in px:
        if max(r, g, b) < threshold:
            out.append((r, g, b, 0))
        else:
            out.append((r, g, b, 255))
    rgba.putdata(out)
    bbox = rgba.getbbox()
    return rgba.crop(bbox) if bbox else rgba


def fit_on_canvas(mark: Image.Image, size: int, bg=(7, 17, 31, 255), pad_ratio: float = 0.14) -> Image.Image:
    canvas = Image.new("RGBA", (size, size), bg)
    pad = max(1, int(size * pad_ratio))
    fitted = mark.copy()
    fitted.thumbnail((size - pad * 2, size - pad * 2), Image.Resampling.LANCZOS)
    x = (size - fitted.width) // 2
    y = (size - fitted.height) // 2
    canvas.paste(fitted, (x, y), fitted)
    return canvas


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    # clean previews
    for old in OUT.glob("*"):
        if old.is_file():
            old.unlink()

    im = Image.open(SRC).convert("RGBA")
    # 16x16 brightness grid: mark is ~cols 6-10, rows 1-5
    crops = {
        "logo-mark": (360, 50, 700, 360),
        "wordmark": (250, 370, 780, 470),
        "primary": (60, 500, 520, 640),
        "icon": (70, 690, 220, 840),
        "app-icon-dark": (560, 690, 720, 850),
        "favicon-circle": (740, 700, 900, 860),
    }

    for name, box in crops.items():
        trimmed = to_transparent(im.crop(box), threshold=16)
        trimmed.save(OUT / f"{name}.png")
        print(name, trimmed.size)

    mark = Image.open(OUT / "logo-mark.png").convert("RGBA")
    for size in (16, 32, 48, 64, 180, 192, 512):
        fit_on_canvas(mark, size).save(OUT / f"icon-{size}.png")

    # Transparent favicon-friendly mark
    fit_on_canvas(mark, 32, bg=(0, 0, 0, 0), pad_ratio=0.08).save(OUT / "favicon.png")

    # Sidebar lockup: mark + wordmark
    mark_s = mark.copy()
    mark_s.thumbnail((56, 56), Image.Resampling.LANCZOS)
    word = Image.open(OUT / "wordmark.png").convert("RGBA")
    word.thumbnail((220, 48), Image.Resampling.LANCZOS)
    h = max(mark_s.height, word.height)
    lockup = Image.new("RGBA", (mark_s.width + 12 + word.width, h), (0, 0, 0, 0))
    lockup.paste(mark_s, (0, (h - mark_s.height) // 2), mark_s)
    lockup.paste(word, (mark_s.width + 12, (h - word.height) // 2), word)
    lockup.save(OUT / "logo-lockup.png")
    print("logo-lockup", lockup.size)
    print("done", OUT)


if __name__ == "__main__":
    main()
