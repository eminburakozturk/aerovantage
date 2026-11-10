# Contributing

Thanks for helping keep AeroVantage release-ready. This project is under **feature / UI freeze** except approved hygiene and bugfixes.

## Ground rules

- No new business features or UI redesigns without explicit approval
- No secrets in commits (`.env`, keys, tokens)
- Prefer small, reviewable diffs

## Setup

```powershell
install.bat
# root .env from .env.example
# frontend/.env.local from frontend/.env.local.example
uvicorn api.main:app --reload
cd frontend; npm run dev
```

## Quality gates (required before PR)

```powershell
python scripts/smoke_demo.py
python -m pytest tests/test_scada.py tests/test_observability.py tests/test_i18n.py -q
cd frontend
npm run lint
npx tsc --noEmit
npm run build
```

CI also runs `.github/workflows/quality-gates.yml` on `main` / `dev`.

## Docs

- Demo: `docs/DEMO-RUNBOOK.md`
- Architecture: `docs/architecture.md`
- Release prep: `docs/RELEASE-CHECKLIST.md`

## Commit hygiene

- Do not commit `frontend/node_modules`, `frontend/.next`, `_checkup/`, or `video_frames/`
- Keep change scope to the problem stated in the PR
