#!/usr/bin/env python3
"""Extract sample frames from a screen recording for visual QA."""

from __future__ import annotations

import sys
from pathlib import Path

import cv2


def main() -> int:
    src = Path(sys.argv[1] if len(sys.argv) > 1 else "").expanduser()
    out = Path(sys.argv[2] if len(sys.argv) > 2 else "video_frames")
    every_s = float(sys.argv[3]) if len(sys.argv) > 3 else 2.0

    if not src.exists():
        print(f"missing video: {src}", file=sys.stderr)
        return 1

    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("frame_*.jpg"):
        old.unlink()

    cap = cv2.VideoCapture(str(src))
    fps = float(cap.get(cv2.CAP_PROP_FPS) or 30.0)
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    dur = n / fps if fps else 0.0
    print(f"fps={fps:.2f} frames={n} duration_s={dur:.1f}")

    interval = max(1, int(round(fps * every_s)))
    saved: list[tuple[float, str]] = []
    i = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if i % interval == 0:
            t = i / fps
            path = out / f"frame_{int(t):04d}s.jpg"
            h, w = frame.shape[:2]
            scale = min(1.0, 1280.0 / w)
            if scale < 1.0:
                frame = cv2.resize(frame, (int(w * scale), int(h * scale)))
            cv2.imwrite(str(path), frame, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
            saved.append((t, path.name))
        i += 1
    cap.release()

    print(f"saved={len(saved)} -> {out}")
    for t, name in saved:
        print(f"{t:6.1f}s  {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
