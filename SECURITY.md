# Security Policy

## Supported versions

| Version | Supported |
|---------|-----------|
| v1.0.x (RC1+) | Yes (pilot) |

## Reporting a vulnerability

Do **not** open a public GitHub issue for secrets or credentials.

1. Rotate any exposed key immediately (EPİAŞ, Gemini/LLM, API Bearer).
2. Contact the repository maintainers privately.
3. Confirm `.env` / `.env.local` are not tracked (`git check-ignore -v .env`).

## Secret handling

| Item | Rule |
|------|------|
| Root `.env` | Local only — gitignored |
| `frontend/.env.local` | Local only — gitignored; **never** commit |
| `API_SECRET_KEY` | Server / BFF only — never `NEXT_PUBLIC_*` |
| LLM / EPİAŞ keys | Root `.env` only |

## Auth model (pilot)

AeroVantage RC1 uses a shared Bearer API key between the Next.js BFF and FastAPI.
This is suitable for local demo / pilot, **not** multi-tenant production IdP.

## Defaults

Docker Compose and local examples may ship a **development** API key string.
Always override secrets before any shared or production-like deployment.
