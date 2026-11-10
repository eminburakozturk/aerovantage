#!/usr/bin/env python3
"""PyInstaller ile logolu AeroVantage.exe derlemesi."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LAUNCHER = ROOT / "launcher" / "app.py"
BUILD_DIR = ROOT / "build" / "pyinstaller"
DIST_DIR = ROOT / "dist"
DIST_EXE = DIST_DIR / "AeroVantage.exe"
OUTPUT_EXE = ROOT / "AeroVantage.exe"
MOCK_MANIFEST = BUILD_DIR / "build-manifest.mock.json"
ICO = ROOT / "AeroVantage.ico"
ASSETS_ICO = ROOT / "launcher" / "assets" / "aerovantage.ico"
TRAY_PNG = ROOT / "launcher" / "assets" / "tray-64.png"


def _print_step(message: str) -> None:
    print(f"[build] {message}")


def _ensure_icons() -> Path | None:
    prepare = ROOT / "scripts" / "prepare_brand_icons.py"
    if prepare.exists():
        subprocess.run([sys.executable, str(prepare)], cwd=ROOT, check=False)
    for candidate in (ICO, ASSETS_ICO):
        if candidate.exists():
            return candidate
    return None


def _write_mock_manifest(reason: str) -> None:
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "mode": "mock",
        "reason": reason,
        "entrypoint": str(LAUNCHER),
        "expected_output": str(OUTPUT_EXE),
        "icon": str(ICO if ICO.exists() else ASSETS_ICO),
    }
    MOCK_MANIFEST.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    _print_step(f"Mock derleme manifesti yazildi: {MOCK_MANIFEST}")


def _pyinstaller_available() -> bool:
    try:
        import PyInstaller  # noqa: F401

        return True
    except ImportError:
        return False


def _sep() -> str:
    return ";" if sys.platform == "win32" else ":"


def build_exe() -> int:
    if not LAUNCHER.exists():
        _print_step(f"HATA: Launcher bulunamadi: {LAUNCHER}")
        return 1

    icon = _ensure_icons()

    if not _pyinstaller_available():
        _print_step("PyInstaller bulunamadi — yukleniyor...")
        pip = subprocess.run(
            [sys.executable, "-m", "pip", "install", "pyinstaller"],
            cwd=ROOT,
            check=False,
        )
        if pip.returncode != 0 or not _pyinstaller_available():
            _print_step("PyInstaller kurulamadi — mock derleme.")
            _write_mock_manifest("PyInstaller kurulu degil")
            return 0

    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    DIST_DIR.mkdir(parents=True, exist_ok=True)

    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--windowed",
        "--name",
        "AeroVantage",
        "--distpath",
        str(DIST_DIR),
        "--workpath",
        str(BUILD_DIR),
        "--specpath",
        str(BUILD_DIR),
        "--hidden-import",
        "pystray",
        "--hidden-import",
        "pystray._base",
        "--hidden-import",
        "pystray._win32",
        "--hidden-import",
        "PIL",
        "--hidden-import",
        "PIL.Image",
        "--hidden-import",
        "PIL.ImageDraw",
        "--hidden-import",
        "requests",
        "--collect-all",
        "pystray",
        "--collect-all",
        "PIL",
        # Keep tray EXE lean — avoid accidental heavy ML pulls via transitive imports
        "--exclude-module",
        "numpy.tests",
        "--exclude-module",
        "tkinter",
        "--exclude-module",
        "matplotlib",
        "--exclude-module",
        "scipy",
        "--exclude-module",
        "pandas",
        "--exclude-module",
        "torch",
        "--exclude-module",
        "tensorflow",
    ]

    if icon is not None:
        command.extend(["--icon", str(icon)])
        _print_step(f"EXE ikonu: {icon}")

    # Frozen exe icinde tray ikonu
    brand_dir = ROOT / "launcher" / "assets"
    if brand_dir.exists():
        command.extend(["--add-data", f"{brand_dir}{_sep()}brand"])

    command.append(str(LAUNCHER))

    _print_step("PyInstaller calistiriliyor...")
    result = subprocess.run(command, cwd=ROOT, check=False)
    if result.returncode != 0:
        _print_step(f"HATA: PyInstaller basarisiz (exit {result.returncode})")
        return result.returncode

    if not DIST_EXE.exists():
        _print_step(f"HATA: Derleme ciktisi bulunamadi: {DIST_EXE}")
        return 1

    shutil.copy2(DIST_EXE, OUTPUT_EXE)
    _print_step(f"AeroVantage.exe hazir: {OUTPUT_EXE}")
    return 0


def main() -> int:
    return build_exe()


if __name__ == "__main__":
    raise SystemExit(main())
