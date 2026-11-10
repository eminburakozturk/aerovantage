"""Demo / RC öncesi tek komut doğrulama paketi.

Çalıştırır:
  1) tests/test_scada.py
  2) scripts/smoke_live_cutover.py
  3) scripts/smoke_gemini_scada_proxy.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _run(label: str, args: list[str]) -> int:
    print()
    print("=" * 60)
    print(f"> {label}")
    print("=" * 60)
    completed = subprocess.run(args, cwd=ROOT)
    status = "OK" if completed.returncode == 0 else "FAIL"
    print(f"< {label}: {status} (exit={completed.returncode})")
    return completed.returncode


def main() -> int:
    py = sys.executable
    steps = [
        ("SCADA unit tests", [py, "-m", "pytest", "tests/test_scada.py", "-q", "--tb=line"]),
        ("Live cutover (EPİAŞ + Weather)", [py, "scripts/smoke_live_cutover.py"]),
        ("Gemini + SCADA simulator", [py, "scripts/smoke_gemini_scada_proxy.py"]),
        ("System live status (health)", [py, "scripts/smoke_system_status.py"]),
    ]
    failures = 0
    for label, args in steps:
        code = _run(label, args)
        if code != 0:
            failures += 1

    print()
    if failures:
        print(f"SONUÇ: {failures}/{len(steps)} adım başarısız — demo öncesi düzelt")
        return 1
    print("SONUÇ: Demo smoke paketi yeşil — EPİAŞ/Weather live, SCADA simulated, Gemini live")
    print("UI turu: docs/DEMO-RUNBOOK.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
