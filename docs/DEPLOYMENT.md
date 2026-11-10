# AeroVantage — Deployment

Primary UI is **Next.js** on port `3000`. Streamlit (`dashboard/`) is legacy and optional.

## Local (recommended)

```powershell
install.bat
AeroVantage-Tray.bat
```

- Frontend: http://localhost:3000  
- API docs: http://127.0.0.1:8000/docs  

Frontend server auth (BFF):

```
# frontend/.env.local
API_BACKEND_URL=http://127.0.0.1:8000
API_SECRET_KEY=<same as root .env>
```

Do **not** put `API_SECRET_KEY` in `NEXT_PUBLIC_*` variables.

## Docker Compose

```powershell
docker compose up --build
```

| Service | Port | Role |
|---------|------|------|
| `api` | 8000 | FastAPI |
| `frontend` | 3000 | Next.js + BFF proxy |

Frontend container injects:

- `API_BACKEND_URL=http://api:8000`
- `API_SECRET_KEY` from host `.env`

### Legacy Streamlit

```powershell
docker compose --profile legacy up --build
```

Streamlit UI: http://localhost:8501

## Health checks

- API: `GET /docs` (container HEALTHCHECK)
- Frontend: `GET /` on port 3000
- Public API health: `GET http://127.0.0.1:8000/health`

## Pre-demo / release gates

```powershell
python scripts/smoke_demo.py
```

Full checklist: [RELEASE-CHECKLIST.md](./RELEASE-CHECKLIST.md)  
Demo UI tour: [DEMO-RUNBOOK.md](./DEMO-RUNBOOK.md)  
SCADA provider architecture: [SCADA-ADAPTER.md](./SCADA-ADAPTER.md)
