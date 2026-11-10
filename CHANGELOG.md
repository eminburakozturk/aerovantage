# Changelog

## 1.0.0-rc1 — 2026-07-14

### Maintenance Mode (G5)
- **v1.x development cycle closed.** Maintenance Mode active ([`docs/V1-MAINTENANCE-POLICY.md`](docs/V1-MAINTENANCE-POLICY.md)).
- Primary future development focus pointer: [`docs/HYPER-CORE.md`](docs/HYPER-CORE.md).
- New product ideas → [`docs/V2-BACKLOG.md`](docs/V2-BACKLOG.md) only.
- Release notes: [`docs/RELEASE-NOTES-v1.0.0-rc1.md`](docs/RELEASE-NOTES-v1.0.0-rc1.md).
- Final report: [`docs/AEROVANTAGE-V1.0-RC1-FINAL-RELEASE-REPORT.md`](docs/AEROVANTAGE-V1.0-RC1-FINAL-RELEASE-REPORT.md).

### Maintenance policy
- **v1.x is Feature Complete.** Further v1.x releases are Bug / Security / Performance / Maintenance only ([`docs/V1-MAINTENANCE-POLICY.md`](docs/V1-MAINTENANCE-POLICY.md)). New product ideas go to [`docs/V2-BACKLOG.md`](docs/V2-BACKLOG.md), not v1.x.

### Release Candidate
- Operational Intelligence UI (Next.js) with TR / EN / DE.
- Daily pipeline: forecast → performance → risk → alerts → AI insight.
- Live EPİAŞ + Open-Meteo; SCADA simulated (provider swap-ready).
- Gemini briefing / report Q&A with playbook fallback.
- Corporate PDF / Excel / CSV reporting with locale-aware exports.
- Observability: degraded mode, confidence, audit and metrics surfaces.
- Quality gates: pytest reliability suites + frontend lint / tsc / build.

### Security / credentials (RC1)
- **Credential Rotation Required Before Production** — EPİAŞ, Gemini/`LLM_API_KEY`, and `API_SECRET_KEY` must be rotated and attested by the operator (`docs/CREDENTIAL-ROTATE.md`) before any production use.
- Fail-closed shared API Bearer: empty defaults in examples; no baked Docker key; compose requires `${API_SECRET_KEY:?…}`.
- RC1 must not be treated as production-credential-ready.

### Repository hygiene (RC1 prep)
- Untracked `frontend/node_modules`, `frontend/.next`, `frontend/.env.local`.
- Strengthened `.gitignore` (frontend build/deps, `_checkup/`, `video_frames/`).
- Added `LICENSE`, `SECURITY.md`, `CONTRIBUTING.md`.
- Refreshed README (EN/TR/DE), architecture (Next.js + BFF), screenshots.
- Removed unused dashboard/workspace components and empty folders.

### Data posture
| Connector | Mode |
|-----------|------|
| EPİAŞ | Live |
| Weather | Live |
| SCADA | Simulated (EPİAŞ-derived) |
| LLM | Gemini live (playbook fallback) |

## 1.0.0 (Sprint 2 baseline)

- Forecast / data pipeline reliability hardening.
- Data contracts, hybrid model workflow, drift / confidence calibration.
- Monitoring audit alignment and recommendation quality proxies.
