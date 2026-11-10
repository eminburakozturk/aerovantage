#!/usr/bin/env python3
"""AeroVantage Developer Experience CLI — install, start, stop."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = ROOT / "frontend"
PID_FILE = ROOT / ".aero.pid"
ENV_FILE = ROOT / ".env"
ENV_EXAMPLE = ROOT / ".env.example"
FRONTEND_ENV_FILE = FRONTEND_DIR / ".env.local"
FRONTEND_ENV_EXAMPLE = FRONTEND_DIR / ".env.local.example"
REQUIREMENTS = ROOT / "requirements.txt"

BACKEND_HOST = "127.0.0.1"
BACKEND_PORT = 8000
FRONTEND_PORT = 3000
HEALTH_URL = f"http://{BACKEND_HOST}:{BACKEND_PORT}/health"
STARTUP_TIMEOUT_SECONDS = 60


class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    GREEN = "\033[32m"
    RED = "\033[31m"
    YELLOW = "\033[33m"
    CYAN = "\033[36m"
    MAGENTA = "\033[35m"


def _configure_stdio() -> None:
    """Windows cp1254 ortaminda Unicode log karakterlerini guvenle yaz."""
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    os.environ.setdefault("PYTHONUTF8", "1")
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except (AttributeError, OSError, ValueError):
            pass


def _enable_windows_ansi() -> None:
    if sys.platform != "win32":
        return
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)
        mode = ctypes.c_uint32()
        kernel32.GetConsoleMode(handle, ctypes.byref(mode))
        kernel32.SetConsoleMode(handle, mode.value | 0x0004)
    except (AttributeError, OSError):
        pass


def log_ok(message: str) -> None:
    print(f"{Colors.GREEN}[OK]{Colors.RESET} {message}", flush=True)


def log_err(message: str) -> None:
    print(f"{Colors.RED}[ERR]{Colors.RESET} {message}", file=sys.stderr, flush=True)


def log_info(message: str) -> None:
    print(f"{Colors.CYAN}[>>]{Colors.RESET} {message}", flush=True)


def log_warn(message: str) -> None:
    print(f"{Colors.YELLOW}[!]{Colors.RESET} {message}", flush=True)


def log_title(message: str) -> None:
    print(f"\n{Colors.BOLD}{Colors.MAGENTA}{message}{Colors.RESET}\n", flush=True)


def _subprocess_env() -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    return env


def run_command(
    command: list[str],
    *,
    cwd: Path | None = None,
    label: str,
) -> None:
    log_info(f"{label}...")
    result = subprocess.run(
        command,
        cwd=cwd or ROOT,
        check=False,
        env=_subprocess_env(),
    )
    if result.returncode != 0:
        raise RuntimeError(f"{label} başarısız (exit code {result.returncode})")


def copy_if_missing(source: Path, target: Path, label: str) -> None:
    if target.exists():
        log_ok(f"{label} zaten mevcut: {target.name}")
        return
    if not source.exists():
        log_warn(f"{label} kaynağı bulunamadı: {source}")
        return
    shutil.copy2(source, target)
    log_ok(f"{label} oluşturuldu: {target.name}")


def ensure_env_files() -> None:
    copy_if_missing(ENV_EXAMPLE, ENV_FILE, "Backend .env")
    if FRONTEND_DIR.exists():
        copy_if_missing(FRONTEND_ENV_EXAMPLE, FRONTEND_ENV_FILE, "Frontend .env.local")


def read_pid_file() -> dict[str, Any]:
    if not PID_FILE.exists():
        return {}
    try:
        return json.loads(PID_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f".aero.pid dosyası okunamadı: {exc}") from exc


def write_pid_file(payload: dict[str, Any]) -> None:
    PID_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def is_process_running(pid: int) -> bool:
    if pid <= 0:
        return False
    if sys.platform == "win32":
        result = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
            check=False,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
        )
        import re

        return bool(re.search(rf',"{pid}",', result.stdout or ""))
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def kill_listeners_on_port(port: int, label: str) -> None:
    """Windows'ta portu dinleyen süreçleri zorla kapatır (PID dosyası kaybolsa bile)."""
    if sys.platform != "win32":
        return
    try:
        result = subprocess.run(
            ["netstat", "-ano"],
            capture_output=True,
            text=True,
            check=False,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
        )
    except OSError as exc:
        log_warn(f"{label} port {port} taranamadı: {exc}")
        return

    pids: set[int] = set()
    needle = f":{port}"
    for line in (result.stdout or "").splitlines():
        if needle not in line or "LISTENING" not in line.upper():
            continue
        parts = line.split()
        if not parts:
            continue
        try:
            pids.add(int(parts[-1]))
        except ValueError:
            continue

    for pid in sorted(pids):
        if pid <= 0:
            continue
        kill_process(pid, f"{label} :{port}")


def kill_process(pid: int, label: str) -> bool:
    if not is_process_running(pid):
        log_warn(f"{label} zaten kapalı (PID {pid})")
        return True

    if sys.platform == "win32":
        result = subprocess.run(
            ["taskkill", "/PID", str(pid), "/F", "/T"],
            capture_output=True,
            text=True,
            check=False,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
        )
        if result.returncode != 0:
            log_err(f"{label} kapatılamadı (PID {pid}): {result.stderr.strip()}")
            return False
    else:
        try:
            os.kill(pid, signal.SIGTERM)
            time.sleep(0.5)
            if is_process_running(pid):
                os.kill(pid, signal.SIGKILL)
        except OSError as exc:
            log_err(f"{label} kapatılamadı (PID {pid}): {exc}")
            return False

    log_ok(f"{label} durduruldu (PID {pid})")
    return True


def wait_for_backend() -> None:
    log_info(f"Backend hazır olana kadar bekleniyor (max {STARTUP_TIMEOUT_SECONDS}s)...")
    deadline = time.time() + STARTUP_TIMEOUT_SECONDS
    while time.time() < deadline:
        try:
            with urlopen(HEALTH_URL, timeout=2) as response:
                if response.status == 200:
                    log_ok(f"Backend hazır: {HEALTH_URL}")
                    return
        except (URLError, TimeoutError, OSError):
            time.sleep(1)
    raise RuntimeError("Backend belirlenen sürede ayaga kalkmadi")


def spawn_process(command: list[str], *, cwd: Path, label: str) -> int:
    creationflags = 0
    if sys.platform == "win32":
        creationflags = subprocess.CREATE_NO_WINDOW

    process = subprocess.Popen(
        command,
        cwd=cwd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=creationflags,
        env=_subprocess_env(),
    )
    log_ok(f"{label} başlatıldı (PID {process.pid})")
    return process.pid


def cmd_install(args: argparse.Namespace) -> int:
    log_title("AeroVantage Install")
    quick = bool(getattr(args, "quick", False))

    ensure_env_files()

    backend_ready = False
    if quick:
        try:
            import fastapi  # noqa: F401
            import uvicorn  # noqa: F401

            backend_ready = True
            log_ok("Backend bagimliliklari guncel (quick)")
        except ImportError:
            log_info("Backend bagimliliklari eksik — pip kurulumu yapilacak")

    if not backend_ready:
        if not REQUIREMENTS.exists():
            log_err(f"requirements.txt bulunamadi: {REQUIREMENTS}")
            return 1

        run_command(
            [sys.executable, "-m", "pip", "install", "--upgrade", "pip"],
            label="pip guncelleme",
        )
        run_command(
            [sys.executable, "-m", "pip", "install", "-r", str(REQUIREMENTS)],
            label="Backend bagimliliklari (pip install)",
        )
        log_ok("Backend bagimliliklari kuruldu")

    if not FRONTEND_DIR.exists():
        log_warn("frontend/ dizini bulunamadi — npm install atlandi")
        log_ok("Kurulum tamamlandi")
        return 0

    next_bin = FRONTEND_DIR / "node_modules" / "next" / "dist" / "bin" / "next"
    if quick and next_bin.exists():
        log_ok("Frontend bagimliliklari guncel (quick)")
        log_ok("Kurulum tamamlandi")
        return 0

    npm = shutil.which("npm")
    if not npm:
        log_err("npm bulunamadi. Node.js kurulumunu kontrol edin.")
        return 1

    run_command(
        [npm, "install", "--legacy-peer-deps"],
        cwd=FRONTEND_DIR,
        label="Frontend bagimliliklari (npm install)",
    )
    log_ok("Frontend bagimliliklari kuruldu")

    log_ok("Kurulum tamamlandi")
    return 0


def ensure_frontend_dependencies() -> None:
    """Frontend node_modules yoksa npm install calistirir."""
    if not FRONTEND_DIR.exists():
        raise RuntimeError("frontend/ dizini bulunamadi")

    next_bin = FRONTEND_DIR / "node_modules" / "next" / "dist" / "bin" / "next"
    if next_bin.exists():
        return

    npm = shutil.which("npm")
    if not npm:
        raise RuntimeError("npm bulunamadi. Once install.bat calistirin.")

    log_warn("Frontend bagimliliklari eksik — npm install calistiriliyor...")
    run_command(
        [npm, "install", "--legacy-peer-deps"],
        cwd=FRONTEND_DIR,
        label="Frontend bagimliliklari (npm install)",
    )


def build_frontend_command() -> list[str]:
    node = shutil.which("node")
    next_bin = FRONTEND_DIR / "node_modules" / "next" / "dist" / "bin" / "next"
    if node and next_bin.exists():
        return [
            node,
            str(next_bin),
            "dev",
            "--port",
            str(FRONTEND_PORT),
            "--hostname",
            BACKEND_HOST,
        ]

    npm = shutil.which("npm")
    if not npm:
        raise RuntimeError("npm bulunamadı")
    return [npm, "run", "dev", "--", "--port", str(FRONTEND_PORT), "--hostname", BACKEND_HOST]


def cmd_start(_: argparse.Namespace) -> int:
    log_title("AeroVantage Start")

    existing = read_pid_file()
    backend_pid = int(existing.get("backend", 0))
    frontend_pid = int(existing.get("frontend", 0))
    if is_process_running(backend_pid) or is_process_running(frontend_pid):
        log_err("AeroVantage zaten çalışıyor. Önce: python scripts/aero.py stop")
        return 1

    ensure_env_files()

    backend_pid = spawn_process(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "api.main:app",
            "--host",
            BACKEND_HOST,
            "--port",
            str(BACKEND_PORT),
        ],
        cwd=ROOT,
        label=f"Backend (uvicorn :{BACKEND_PORT})",
    )

    try:
        wait_for_backend()
    except RuntimeError as exc:
        log_err(str(exc))
        kill_process(backend_pid, "Backend")
        return 1

    if not FRONTEND_DIR.exists():
        log_err("frontend/ dizini bulunamadı")
        kill_process(backend_pid, "Backend")
        return 1

    try:
        ensure_frontend_dependencies()
    except RuntimeError as exc:
        log_err(str(exc))
        kill_process(backend_pid, "Backend")
        return 1

    try:
        frontend_command = build_frontend_command()
    except RuntimeError as exc:
        log_err(str(exc))
        kill_process(backend_pid, "Backend")
        return 1

    frontend_pid = spawn_process(
        frontend_command,
        cwd=FRONTEND_DIR,
        label=f"Frontend (next dev :{FRONTEND_PORT})",
    )

    write_pid_file(
        {
            "backend": backend_pid,
            "frontend": frontend_pid,
            "backend_url": f"http://{BACKEND_HOST}:{BACKEND_PORT}",
            "frontend_url": f"http://{BACKEND_HOST}:{FRONTEND_PORT}",
            "started_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }
    )

    print()
    log_ok(f"Backend  → http://{BACKEND_HOST}:{BACKEND_PORT}/docs")
    log_ok(f"Frontend → http://{BACKEND_HOST}:{FRONTEND_PORT}")
    log_ok(f"PID dosyası → {PID_FILE.name}")
    return 0


def cmd_stop(_: argparse.Namespace) -> int:
    log_title("AeroVantage Stop")

    backend_ok = True
    frontend_ok = True

    if PID_FILE.exists():
        payload = read_pid_file()
        backend_pid = int(payload.get("backend", 0))
        frontend_pid = int(payload.get("frontend", 0))
        backend_ok = kill_process(backend_pid, "Backend") if backend_pid else True
        frontend_ok = kill_process(frontend_pid, "Frontend") if frontend_pid else True
        try:
            PID_FILE.unlink(missing_ok=True)
            log_ok(".aero.pid temizlendi")
        except OSError as exc:
            log_warn(f".aero.pid silinemedi: {exc}")
    else:
        log_warn(".aero.pid bulunamadı — port temizliği deneniyor")

    # PID kaybolsa / orphan kalsa bile 8000 ve 3000'i serbest bırak
    kill_listeners_on_port(BACKEND_PORT, "Backend")
    kill_listeners_on_port(FRONTEND_PORT, "Frontend")

    if backend_ok and frontend_ok:
        log_ok("Tüm süreçler durduruldu")
        return 0

    return 1


def cmd_status(_: argparse.Namespace) -> int:
    try:
        with urlopen(HEALTH_URL, timeout=2) as response:
            return 0 if response.status == 200 else 1
    except (URLError, TimeoutError, OSError):
        return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aero",
        description="AeroVantage Developer Experience CLI",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    install_parser = subparsers.add_parser("install", help="Backend ve frontend bagimliliklarini kur")
    install_parser.add_argument(
        "--quick",
        action="store_true",
        help="Mevcut backend/frontend bagimliliklarini atla",
    )
    install_parser.set_defaults(func=cmd_install)

    status_parser = subparsers.add_parser("status", help="Servislerin calisip calismadigini kontrol et")
    status_parser.set_defaults(func=cmd_status)

    start_parser = subparsers.add_parser("start", help="Backend ve frontend'i baslat")
    start_parser.set_defaults(func=cmd_start)

    stop_parser = subparsers.add_parser("stop", help="Çalışan süreçleri durdur")
    stop_parser.set_defaults(func=cmd_stop)

    return parser


def main() -> int:
    _configure_stdio()
    _enable_windows_ansi()
    os.chdir(ROOT)
    parser = build_parser()
    args = parser.parse_args()
    try:
        return int(args.func(args))
    except RuntimeError as exc:
        log_err(str(exc))
        return 1
    except KeyboardInterrupt:
        print()
        log_warn("İşlem kullanıcı tarafından iptal edildi")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
