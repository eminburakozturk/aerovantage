# AeroVantage v1.0.0-rc1 — Release Notes

**Release Candidate 1** · **2026-07-14**  
**Tag:** `v1.0.0-rc1`  
**Policy:** Feature Complete / Maintenance Mode — [`V1-MAINTENANCE-POLICY.md`](V1-MAINTENANCE-POLICY.md)

---

## Highlights

- Operational Intelligence console (Next.js) with Turkish / English / German.
- Daily decision pipeline: forecast → performance → risk → alerts → AI insight.
- Live EPİAŞ market/generation and Open-Meteo weather; SCADA simulated and swap-ready.
- Gemini-backed briefing and report Q&A with playbook fallback.
- Corporate PDF / Excel / CSV reporting with locale-aware exports.
- Observability surfaces: health, degraded mode, confidence, audit, and metrics.
- Quality gates: frontend lint / TypeScript / build + pytest reliability suites.
- Fail-closed API Bearer posture (no baked default key); operator rotation required before production.

---

## Architecture

| Layer | Stack |
|-------|--------|
| UI | Next.js App Router, TypeScript (`strict`), Tailwind |
| BFF | Next.js Route Handlers — server-only `API_SECRET_KEY` |
| API | FastAPI (routing) + `modules/*` domain + `core/pipeline.py` |
| Packaging | Docker Compose; optional Windows tray / installer |

The browser never holds API secrets. BFF injects Bearer auth toward FastAPI. FAZ 1–7 of the locked final roadmap are complete; the development cycle for new product scope on v1.x is closed.

---

## AI

- Provider: Google Gemini (configurable), with automatic playbook fallback.
- Surfaces: operational briefing, decision support hints, report Q&A.
- Knowledge / playbook layer supports offline-safe demo narration.
- **Limitation:** LLM quality depends on live credentials and provider availability; empty or invalid keys degrade to playbook mode.

---

## Forecast

- Production / weather forecast views in the ops console.
- Reliability gates: walk-forward / model reliability enforcement on the pipeline path.
- Hybrid XGB may fall back to physics when artifacts are missing (documented Known Limitation).
- Weather live via Open-Meteo; EPİAŞ live for market-aligned context.

---

## Risk

- Financial and production deviation analysis on the daily pipeline.
- Decision / recommendation quality proxies and risk explainability hooks.
- Alerting tied to pipeline outcomes for operator attention.

---

## Reports

- Executive and typed report packs.
- Export: PDF, Excel, CSV — locale-aware (tr / en / de).
- Report Q&A via AI layer when credentials allow.

---

## Monitoring

- Health endpoints for connector posture (EPİAŞ / weather / SCADA modes).
- Degraded-mode and observability summaries.
- Drift / confidence stack surfaces for model monitoring.
- SCADA remains **simulated** in RC1 (adapter ready for REST provider swap).

---

## Known Limitations

- SCADA is simulated (EPİAŞ-derived), not live plant telemetry.
- National wind → plant scale approximation — not site-specific SCADA actuals.
- Auth is a shared API Bearer (pilot) — not corporate IdP / RBAC.
- Hybrid XGB may fall back to physics without model artifacts.
- LLM uses Gemini with playbook fallback.
- Streamlit UI is legacy-only; primary product UI is Next.js.
- CORS is localhost-oriented for demo / pilot.
- **RC1 is not production-credential-ready** until operators rotate EPİAŞ / Gemini / `API_SECRET_KEY` and attest via [`CREDENTIAL-ROTATE.md`](CREDENTIAL-ROTATE.md).

---

## Maintenance Policy

AeroVantage **v1.x is Feature Complete** and in **Maintenance Mode**.

| Allowed | Not allowed |
|---------|-------------|
| Bug / security / performance / docs / tests / safe dependency updates | New dashboards, workspaces, AI modules, data sources, business features |

- Policy: [`V1-MAINTENANCE-POLICY.md`](V1-MAINTENANCE-POLICY.md)
- New product ideas: [`V2-BACKLOG.md`](V2-BACKLOG.md) — do **not** implement on v1.x
- Primary future development focus: **Hyper Core** (see [`HYPER-CORE.md`](HYPER-CORE.md))

---

## Packages

| Package | Path | Audience |
|---------|------|----------|
| GitHub source bundle | `release/github/` | Public / OSS-style handoff |
| Product showcase | `release/product/` | Brochure / executive materials |

---

## Install / verify (quick)

```powershell
# Backend smoke
python scripts/smoke_demo.py

# Frontend gates
cd frontend
npm run lint
npx tsc --noEmit
npm run build
```

Full checklist: [`RELEASE-CHECKLIST.md`](RELEASE-CHECKLIST.md) · Demo: [`DEMO-RUNBOOK.md`](DEMO-RUNBOOK.md)

---

## GitHub Release (when `gh` is available)

Prepared body file: [`release/github/RELEASE-NOTES-v1.0.0-rc1.md`](../release/github/RELEASE-NOTES-v1.0.0-rc1.md)  
Exact command documented in the Final Release Report.

```text
gh release create v1.0.0-rc1 --title "AeroVantage v1.0.0-rc1" --notes-file release/github/RELEASE-NOTES-v1.0.0-rc1.md
```
