/**
 * Server-only backend bağlantı ayarları.
 * Bu modül yalnızca Next.js Route Handler / Server Component içinde import edilmeli.
 */

function trimTrailingSlash(value: string): string {
  return value.replace(/\/+$/, "");
}

/** FastAPI kök adresi (örn. http://127.0.0.1:8000). */
export function getBackendOrigin(): string {
  const explicit = process.env.API_BACKEND_URL?.trim();
  if (explicit) {
    return trimTrailingSlash(explicit);
  }

  const legacyPublic = process.env.NEXT_PUBLIC_API_BASE_URL?.trim();
  if (legacyPublic) {
    return trimTrailingSlash(legacyPublic.replace(/\/api\/v1\/?$/, ""));
  }

  return "http://127.0.0.1:8000";
}

/** FastAPI Bearer anahtarı — yalnızca server-only `API_SECRET_KEY` (zorunlu). */
export function getApiSecretKey(): string {
  const key = process.env.API_SECRET_KEY?.trim();
  if (key) {
    return key;
  }
  throw new Error(
    "API_SECRET_KEY is required (set in frontend/.env.local or container env). No default key.",
  );
}

export function backendAuthHeaders(extra?: HeadersInit): HeadersInit {
  return {
    Authorization: `Bearer ${getApiSecretKey()}`,
    ...extra,
  };
}
