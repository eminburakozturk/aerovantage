#!/usr/bin/env python3
"""AeroVantage Executive System Tray Launcher — sessiz arka plan başlatıcı."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

import pystray
import requests
from PIL import Image, ImageDraw
from pystray import MenuItem as item

ROOT = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent.parent
AERO_SCRIPT = ROOT / "scripts" / "aero.py"
LOG_DIR = ROOT / "launcher" / "logs"
LOG_FILE = LOG_DIR / "aero.log"

BACKEND_HEALTH_URL = "http://127.0.0.1:8000/health"
FRONTEND_URL = "http://127.0.0.1:3000"
DASHBOARD_URL = "http://127.0.0.1:3000"

_shutdown_event = threading.Event()
_browser_opened = threading.Event()
_stopping = threading.Event()
_tray_icon: pystray.Icon | None = None
_TRAY_LOCK_FILE = ROOT / "launcher" / ".tray.lock"
_python_exe_cache: str | None = None


def _subprocess_env() -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    return env


def _hidden_subprocess_flags() -> int:
    if sys.platform == "win32":
        return subprocess.CREATE_NO_WINDOW
    return 0


def _append_log(message: str) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    with LOG_FILE.open("a", encoding="utf-8") as handle:
        handle.write(f"[{timestamp}] {message}\n")


def _python_executable() -> str:
    """System Python for aero.py — never the frozen AeroVantage.exe."""
    global _python_exe_cache
    if not getattr(sys, "frozen", False):
        return sys.executable
    if _python_exe_cache is not None:
        return _python_exe_cache

    candidates: list[str] = []

    py_launcher = shutil.which("py")
    if py_launcher:
        try:
            probe = subprocess.run(
                [py_launcher, "-3", "-c", "import sys; print(sys.executable)"],
                capture_output=True,
                text=True,
                check=False,
                creationflags=_hidden_subprocess_flags(),
                timeout=10.0,
            )
            path = (probe.stdout or "").strip()
            if probe.returncode == 0 and path and Path(path).exists():
                candidates.append(path)
        except (OSError, subprocess.TimeoutExpired) as exc:
            _append_log(f"py -3 sorgusu basarisiz: {exc}")

    for name in ("python", "python3"):
        found = shutil.which(name)
        if found:
            candidates.append(found)

    if sys.platform == "win32":
        local = os.environ.get("LOCALAPPDATA", "")
        pf = os.environ.get("ProgramFiles", r"C:\Program Files")
        common_roots = [
            Path(local) / "Programs" / "Python" if local else None,
            Path(pf) / "Python312",
            Path(pf) / "Python311",
            Path(pf) / "Python310",
            Path(r"C:\Python312"),
            Path(r"C:\Python311"),
        ]
        for root in common_roots:
            if root is None or not root.exists():
                continue
            for exe in (root / "python.exe",):
                if exe.exists():
                    candidates.append(str(exe))
            # e.g. %LOCALAPPDATA%\Programs\Python\Python312\python.exe
            if root.name == "Python":
                for child in sorted(root.glob("Python*/python.exe"), reverse=True):
                    candidates.append(str(child))

    seen: set[str] = set()
    for candidate in candidates:
        key = candidate.lower()
        if key in seen:
            continue
        seen.add(key)
        # Skip the frozen EXE itself
        if getattr(sys, "frozen", False) and Path(candidate).resolve() == Path(sys.executable).resolve():
            continue
        try:
            probe = subprocess.run(
                [candidate, "-c", "import sys; print(sys.version)"],
                capture_output=True,
                text=True,
                check=False,
                creationflags=_hidden_subprocess_flags(),
                timeout=10.0,
            )
            if probe.returncode == 0:
                _python_exe_cache = candidate
                _append_log(f"Sistem Python bulundu: {candidate}")
                return candidate
        except (OSError, subprocess.TimeoutExpired):
            continue

    msg = (
        "Frozen AeroVantage.exe icin sistem Python bulunamadi. "
        "Python 3'u PATH'e ekleyin veya https://www.python.org/downloads/ adresinden kurun, "
        "ardindan install.bat calistirin."
    )
    _append_log(msg)
    raise FileNotFoundError(msg)


def _run_aero_command(command: str, *, timeout_seconds: float = 45.0) -> None:
    if not AERO_SCRIPT.exists():
        raise FileNotFoundError(f"aero.py bulunamadı: {AERO_SCRIPT}")

    python = _python_executable()
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as log_handle:
        log_handle.write(f"\n--- aero.py {command} ---\n")
        log_handle.flush()
        subprocess.run(
            [python, str(AERO_SCRIPT), command],
            cwd=ROOT,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            check=False,
            creationflags=_hidden_subprocess_flags(),
            env=_subprocess_env(),
            timeout=timeout_seconds,
        )


def _services_ready() -> bool:
    try:
        backend = requests.get(BACKEND_HEALTH_URL, timeout=2)
        if backend.status_code != 200:
            return False
        frontend = requests.get(FRONTEND_URL, timeout=2)
        return frontend.status_code < 500
    except requests.RequestException:
        return False


def _start_services_hidden() -> None:
    if _services_ready():
        _append_log("Servisler zaten calisiyor — aero.py start atlandi")
        return

    _append_log("Tray launcher baslatildi — aero.py start cagriliyor")
    python = _python_executable()
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_handle = LOG_FILE.open("a", encoding="utf-8")
    log_handle.write("\n--- aero.py start (tray) ---\n")
    log_handle.flush()
    process = subprocess.Popen(
        [python, str(AERO_SCRIPT), "start"],
        cwd=ROOT,
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        creationflags=_hidden_subprocess_flags(),
        env=_subprocess_env(),
    )
    _append_log(f"aero.py start arka planda tetiklendi (PID {process.pid})")


def _brand_asset_candidates() -> list[Path]:
    candidates: list[Path] = []
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            base = Path(meipass)
            candidates.extend(
                [
                    base / "brand" / "aerovantage.ico",
                    base / "brand" / "tray-64.png",
                    base / "brand" / "icon-64.png",
                ]
            )
    candidates.extend(
        [
            ROOT / "launcher" / "assets" / "aerovantage.ico",
            ROOT / "launcher" / "assets" / "tray-64.png",
            ROOT / "AeroVantage.ico",
            ROOT / "frontend" / "public" / "brand" / "aerovantage.ico",
            ROOT / "frontend" / "public" / "brand" / "icon-64.png",
            ROOT / "frontend" / "public" / "brand" / "logo-mark.png",
        ]
    )
    return candidates


def _create_tray_image() -> Image.Image:
    for path in _brand_asset_candidates():
        if not path.exists():
            continue
        try:
            image = Image.open(path).convert("RGBA")
            if path.suffix.lower() == ".ico":
                # En buyuk frame
                image.seek(0)
                best = image.copy()
                try:
                    idx = 0
                    while True:
                        image.seek(idx)
                        frame = image.copy()
                        if frame.size[0] >= best.size[0]:
                            best = frame
                        idx += 1
                except EOFError:
                    pass
                image = best.convert("RGBA")
            return image.resize((64, 64), Image.Resampling.LANCZOS)
        except OSError as exc:
            _append_log(f"Brand tray icon okunamadi ({path.name}): {exc}")

    size = 64
    image = Image.new("RGBA", (size, size), (7, 17, 31, 255))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((6, 6, 58, 58), radius=14, fill=(10, 27, 46, 255), outline=(0, 184, 255, 200), width=2)
    draw.polygon([(32, 14), (48, 48), (16, 48)], fill=(47, 128, 255, 255))
    draw.polygon([(32, 22), (42, 44), (22, 44)], fill=(0, 209, 178, 220))
    return image


def _open_dashboard(_icon: pystray.Icon, _menu_item: object) -> None:
    if _services_ready():
        webbrowser.open(DASHBOARD_URL)
        _append_log(f"Dashboard açıldı: {DASHBOARD_URL}")
        return
    _append_log("Dashboard istenildi ama servisler henüz hazır değil")
    # Kullanıcıya tray tooltip ile durum
    if _tray_icon is not None:
        _tray_icon.title = "AeroVantage — starting servers…"
    webbrowser.open(DASHBOARD_URL)


def _view_logs(_icon: pystray.Icon, _menu_item: object) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    if not LOG_FILE.exists():
        LOG_FILE.write_text("No log entries yet.\n", encoding="utf-8")

    if sys.platform == "win32":
        os.startfile(LOG_FILE)  # noqa: S606
    else:
        webbrowser.open(LOG_FILE.as_uri())
    _append_log("Log dosyası açıldı")


def _hard_exit() -> None:
    """Windows pystray bazen icon.stop() sonrası run() döngüsünde kalır."""
    _release_tray_lock()
    _append_log("Tray hard exit")
    os._exit(0)


def _stop_and_exit(icon: pystray.Icon, _menu_item: object) -> None:
    """Menü callback'inde bloklama yok — arka planda stop + zorla çık."""
    if _stopping.is_set():
        _append_log("Stop zaten devam ediyor — hard exit")
        _hard_exit()
        return

    _stopping.set()
    _shutdown_event.set()
    _append_log("Stop & Exit seçildi — arka planda kapanış")
    icon.title = "AeroVantage — shutting down…"

    # Watchdog: stop takılırsa yine de çık (Windows pystray / aero stop kilitlenmesi)
    def _watchdog() -> None:
        time.sleep(12.0)
        if _stopping.is_set():
            _append_log("Stop watchdog — hard exit (12s)")
            try:
                icon.visible = False
                icon.stop()
            except Exception:
                pass
            _hard_exit()

    threading.Thread(target=_watchdog, name="aero-tray-watchdog", daemon=True).start()

    def _shutdown() -> None:
        try:
            _run_aero_command("stop", timeout_seconds=8.0)
            _append_log("aero.py stop tamamlandı")
        except subprocess.TimeoutExpired:
            _append_log("aero.py stop zaman aşımı — port temizliği")
            try:
                _run_aero_command("stop", timeout_seconds=5.0)
            except Exception as exc:  # noqa: BLE001
                _append_log(f"ikinci stop hatası: {exc}")
        except Exception as exc:  # noqa: BLE001
            _append_log(f"aero.py stop hatası: {exc}")
        finally:
            _release_tray_lock()
            try:
                icon.visible = False
                icon.stop()
            except Exception as exc:  # noqa: BLE001
                _append_log(f"icon.stop hatası: {exc}")
            time.sleep(0.2)
            _hard_exit()

    threading.Thread(target=_shutdown, name="aero-tray-shutdown", daemon=True).start()


def _health_watcher() -> None:
    _append_log(f"Health watcher basladi: {BACKEND_HEALTH_URL} + {FRONTEND_URL}")
    waited = 0
    while not _shutdown_event.is_set():
        ready = _services_ready()
        if ready and not _browser_opened.is_set():
            _browser_opened.set()
            webbrowser.open(DASHBOARD_URL)
            _append_log(f"Sistem hazir — tarayici acildi: {DASHBOARD_URL}")
            if _tray_icon is not None:
                _tray_icon.title = "AeroVantage Operational Intelligence"
        elif not ready and waited > 0 and waited % 15 == 0:
            _append_log(f"Servisler henüz hazır değil (beklenen ~{waited}s)")
            if _tray_icon is not None and not _stopping.is_set():
                _tray_icon.title = f"AeroVantage — starting… ({waited}s)"
        time.sleep(1)
        waited += 1
    _append_log("Health watcher durdu")


def _is_tray_process_running(pid: int) -> bool:
    if pid <= 0:
        return False
    if sys.platform != "win32":
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False
    result = subprocess.run(
        ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
        capture_output=True,
        text=True,
        check=False,
        creationflags=_hidden_subprocess_flags(),
    )
    # CSV satırı: "pythonw.exe","1234",... — alt dize yanlış eşleşmesin
    return bool(re.search(rf',"{pid}",', result.stdout or ""))


def _acquire_tray_lock() -> bool:
    """Ayni makinede tek tray ornegi — PID kilidi."""
    _TRAY_LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    if _TRAY_LOCK_FILE.exists():
        try:
            existing_pid = int(_TRAY_LOCK_FILE.read_text(encoding="utf-8").strip())
            if _is_tray_process_running(existing_pid):
                return False
            _append_log(f"Bayat tray kilidi temizlendi (PID {existing_pid})")
        except (OSError, ValueError):
            pass
        _TRAY_LOCK_FILE.unlink(missing_ok=True)
    _TRAY_LOCK_FILE.write_text(str(os.getpid()), encoding="utf-8")
    return True


def _release_tray_lock() -> None:
    try:
        if _TRAY_LOCK_FILE.exists():
            current = _TRAY_LOCK_FILE.read_text(encoding="utf-8").strip()
            if current == str(os.getpid()):
                _TRAY_LOCK_FILE.unlink(missing_ok=True)
    except OSError:
        pass


def main() -> int:
    os.chdir(ROOT)
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    os.environ.setdefault("PYTHONUTF8", "1")
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    if not _acquire_tray_lock():
        # Kilitli tray varsa: servis ayaktaysa panoyu aç; değilse kilidi zorla al
        if _services_ready():
            webbrowser.open(DASHBOARD_URL)
            _append_log("Tray zaten acik + servisler ayakta — pano acildi")
            return 0
        _append_log("Tray kilidi var ama servis yok — kilit sifirlaniyor")
        _TRAY_LOCK_FILE.unlink(missing_ok=True)
        if not _acquire_tray_lock():
            webbrowser.open(DASHBOARD_URL)
            return 0

    _start_services_hidden()

    watcher = threading.Thread(target=_health_watcher, name="aero-health-watcher", daemon=True)
    watcher.start()

    menu = pystray.Menu(
        item("Open Dashboard", _open_dashboard, default=True),
        item("View Logs", _view_logs),
        pystray.Menu.SEPARATOR,
        item("Stop and Exit", _stop_and_exit),
    )

    global _tray_icon
    _tray_icon = pystray.Icon(
        "AeroVantage",
        _create_tray_image(),
        "AeroVantage — starting…",
        menu,
    )

    try:
        _tray_icon.run()
    finally:
        _shutdown_event.set()
        _release_tray_lock()
        if not _stopping.is_set():
            try:
                _run_aero_command("stop", timeout_seconds=20.0)
            except Exception:
                pass

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        try:
            _append_log(f"Tray baslatma hatasi: {exc}")
            _release_tray_lock()
        except Exception:
            pass
        raise
