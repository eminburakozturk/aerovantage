#!/usr/bin/env python3
"""Tray launcher — dogru pythonw yolunu cozumler ve app.py'yi arka planda baslatir."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "launcher" / "app.py"


def _resolve_pythonw() -> str:
    candidate = Path(sys.executable).with_name("pythonw.exe")
    if candidate.exists():
        return str(candidate)
    pyw = shutil.which("pyw")
    if pyw:
        return pyw
    return sys.executable


def main() -> int:
    if not APP.exists():
        print(f"[HATA] launcher bulunamadi: {APP}", file=sys.stderr)
        return 1

    executable = _resolve_pythonw()
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"

    creationflags = 0
    if sys.platform == "win32":
        creationflags = subprocess.CREATE_NO_WINDOW if executable == sys.executable else 0

    subprocess.Popen(
        [executable, str(APP)],
        cwd=ROOT,
        env=env,
        creationflags=creationflags,
        close_fds=False,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
