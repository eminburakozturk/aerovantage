# Credential Rotation — RC1 Gate

> Operator attestation document. Remote provider passwords/API keys must be rotated by the human owning the accounts. This repo no longer ships a default `API_SECRET_KEY`.

## 1) Local / shared API Bearer (`API_SECRET_KEY`)

```powershell
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

1. Put the value in root `.env` as `API_SECRET_KEY=...`
2. Put the **same** value in `frontend/.env.local`
3. Restart API + frontend (or Docker stack with `API_SECRET_KEY` in env)
4. Confirm old string `aerovantage-local-dev-key` appears **nowhere** in runtime config

## 2) EPİAŞ

If username/password were ever shared in chat, logs, or screenshots:

1. Change EPİAŞ portal password
2. Update `EPIAS_USERNAME` / `EPIAS_PASSWORD` in local `.env` only
3. Set `EPIAS_USE_MOCK=false` for live demo
4. Do **not** commit `.env`

## 3) Gemini / LLM

1. Rotate or revoke old Google AI / Gemini key in Cloud console
2. Create new key → `LLM_API_KEY` in `.env`
3. `LLM_PROVIDER=gemini`
4. Run `python scripts/smoke_demo.py`

## 4) Attestation (operator)

| Action | Done (date) | Initials |
|--------|-------------|----------|
| Generated new `API_SECRET_KEY` (no repo default) | | |
| Updated `.env` + `frontend/.env.local` | | |
| Rotated EPİAŞ password (if exposed) | | |
| Rotated Gemini API key (if exposed) | | |
| Verified smoke + health with new secrets | | |

**Code gate (engineering):** hardcoded `aerovantage-local-dev-key` removed from config/Docker/BFF (2026-07-14).
