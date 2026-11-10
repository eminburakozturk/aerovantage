#!/usr/bin/env python3
"""Masaustu, Baslat menusu ve repo-kok logolu kisayollar."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXE = ROOT / "AeroVantage.exe"
BAT = ROOT / "AeroVantage-Tray.bat"
INSTALL_BAT = ROOT / "install.bat"
ICO = ROOT / "AeroVantage.ico"
ASSETS_ICO = ROOT / "launcher" / "assets" / "aerovantage.ico"


def _icon() -> Path:
    for p in (ICO, ASSETS_ICO):
        if p.exists():
            return p
    return ICO


def _icon_location(icon: Path) -> str:
    # Index 0 = primary frame in multi-size .ico
    return f"{icon},0"


def _launch_target() -> Path:
    if EXE.exists():
        return EXE
    return BAT


def _write_shortcut(shell: object, path: Path, target: Path, icon: Path, description: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    shortcut = shell.CreateShortCut(str(path))
    shortcut.Targetpath = str(target)
    shortcut.WorkingDirectory = str(ROOT)
    shortcut.Description = description
    if icon.exists():
        shortcut.IconLocation = _icon_location(icon)
    shortcut.save()
    print(f"[setup] Kisayol: {path}")


def create_shortcuts() -> int:
    try:
        from win32com.client import Dispatch  # type: ignore
    except ImportError:
        return _create_via_powershell()

    icon = _icon()
    target = _launch_target()
    shell = Dispatch("WScript.Shell")

    desktop = Path(shell.SpecialFolders("Desktop"))
    start_menu = Path(shell.SpecialFolders("StartMenu")) / "Programs" / "AeroVantage"
    start_menu.mkdir(parents=True, exist_ok=True)

    desc = "AeroVantage Operational Intelligence"
    surfaces = [
        (desktop / "AeroVantage.lnk", target, desc),
        (start_menu / "AeroVantage.lnk", target, desc),
        # Repo root — Explorer'da logolu baslatma (bat ikon tutamaz)
        (ROOT / "AeroVantage.lnk", target, desc),
    ]
    if INSTALL_BAT.exists():
        surfaces.append(
            (
                start_menu / "AeroVantage Kurulum.lnk",
                INSTALL_BAT,
                "AeroVantage bagimlilik kurulumu",
            )
        )
        surfaces.append(
            (
                ROOT / "AeroVantage-Install.lnk",
                INSTALL_BAT,
                "AeroVantage bagimlilik kurulumu",
            )
        )

    for path, tgt, description in surfaces:
        _write_shortcut(shell, path, tgt, icon, description)

    return 0


def _create_via_powershell() -> int:
    icon = _icon()
    target = _launch_target()
    icon_loc = _icon_location(icon) if icon.exists() else ""
    rows: list[tuple[str, str, str]] = [
        ("__DESKTOP__", str(target), "AeroVantage Operational Intelligence"),
        ("__START__", str(target), "AeroVantage Operational Intelligence"),
        ("__ROOT__", str(target), "AeroVantage Operational Intelligence"),
    ]
    if INSTALL_BAT.exists():
        rows.append(("__START_INSTALL__", str(INSTALL_BAT), "AeroVantage bagimlilik kurulumu"))
        rows.append(("__ROOT_INSTALL__", str(INSTALL_BAT), "AeroVantage bagimlilik kurulumu"))

    # Serialize as TSV for PowerShell
    tsv = "\n".join(f"{k}\t{t}\t{d}" for k, t, d in rows)
    ps = f"""
$W = New-Object -ComObject WScript.Shell
$Desktop = [Environment]::GetFolderPath('Desktop')
$Start = Join-Path ([Environment]::GetFolderPath('StartMenu')) 'Programs\\AeroVantage'
$Root = '{ROOT}'
New-Item -ItemType Directory -Force -Path $Start | Out-Null
$map = @{{
  '__DESKTOP__' = (Join-Path $Desktop 'AeroVantage.lnk')
  '__START__' = (Join-Path $Start 'AeroVantage.lnk')
  '__ROOT__' = (Join-Path $Root 'AeroVantage.lnk')
  '__START_INSTALL__' = (Join-Path $Start 'AeroVantage Kurulum.lnk')
  '__ROOT_INSTALL__' = (Join-Path $Root 'AeroVantage-Install.lnk')
}}
@'
{tsv}
'@ -split "`n" | ForEach-Object {{
  if (-not $_.Trim()) {{ return }}
  $parts = $_.Split("`t")
  $lnk = $map[$parts[0]]
  if (-not $lnk) {{ return }}
  $s = $W.CreateShortcut($lnk)
  $s.TargetPath = $parts[1]
  $s.WorkingDirectory = $Root
  $s.Description = $parts[2]
  if ('{icon_loc}') {{ $s.IconLocation = '{icon_loc}' }}
  $s.Save()
  Write-Host "[setup] Kisayol:" $lnk
}}
"""
    result = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
        cwd=ROOT,
        check=False,
    )
    return result.returncode


def main() -> int:
    return create_shortcuts()


if __name__ == "__main__":
    raise SystemExit(main())
