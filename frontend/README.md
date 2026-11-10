# AeroVantage Frontend — Energy Control Center

Next.js 15 + TypeScript + Tailwind CSS + shadcn/ui (New York / Zinc).

## Çalıştırma

Kök dizinden:

1. `install.bat`
2. `AeroVantage-Tray.bat` (veya `AeroVantage.exe`)

Frontend otomatik olarak `http://localhost:3000` adresinde açılır.

## Geliştirici (manuel)

```powershell
cd C:\Users\Burak\aerovantage
python scripts/aero.py start
```

| Servis | Adres |
|--------|--------|
| Frontend | http://localhost:3000 |
| API | http://127.0.0.1:8000/docs |

## Ortam değişkenleri

```powershell
copy .env.local.example .env.local
```

| Değişken | Varsayılan | Not |
|----------|------------|-----|
| `API_BACKEND_URL` | `http://127.0.0.1:8000` | Server-only BFF hedefi |
| `API_SECRET_KEY` | Required — generate with `secrets.token_urlsafe(32)`. No default. |

Tarayıcı istekleri `/api/backend/*` BFF proxy üzerinden gider; bearer secret istemci bundle'ına girmez.

Docker: `docs/DEPLOYMENT.md` — birincil UI Next.js (`Dockerfile.frontend`).

## Stack

- **Next.js 15** — App Router, `src/` dizini
- **Tailwind CSS** — `darkMode: "class"`, arka plan `#09090B`
- **shadcn/ui** — New York stili, Zinc renk paleti
- **Fontlar** — Inter (UI), JetBrains Mono (veri/monospace)
- **Tremor** — Metrik kartları, risk gauge, dashboard grafikleri
