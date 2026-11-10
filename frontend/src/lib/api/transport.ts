import { ApiError } from "./errors";

function buildClientHeaders(extra?: HeadersInit): HeadersInit {
  return {
    Accept: "application/json",
    "Content-Type": "application/json",
    ...extra,
  };
}

function formatApiDetail(detail: unknown): string {
  if (typeof detail === "string") {
    return detail;
  }
  if (!detail || typeof detail !== "object") {
    return String(detail ?? "");
  }

  const record = detail as Record<string, unknown>;
  const message = typeof record.message === "string" ? record.message : "";

  const dq = record.data_quality as { score?: number; critical_failures?: string[] } | undefined;
  if (dq) {
    const failures = dq.critical_failures?.slice(0, 2).join("; ") ?? "";
    const score = dq.score != null ? ` (skor: ${dq.score})` : "";
    return failures
      ? `data quality gate failed${score}: ${failures}`
      : message || `data quality gate failed${score}`;
  }

  const modelReliability = record.model_reliability as { critical_failures?: string[] } | undefined;
  if (modelReliability?.critical_failures?.length) {
    return `model reliability gate failed: ${modelReliability.critical_failures.slice(0, 2).join("; ")}`;
  }

  const decisionReliability = record.decision_reliability as { critical_failures?: string[] } | undefined;
  if (decisionReliability?.critical_failures?.length) {
    return `decision reliability gate failed: ${decisionReliability.critical_failures.slice(0, 2).join("; ")}`;
  }

  return message || JSON.stringify(detail);
}

async function parseResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const payload = (await response.json()) as { detail?: unknown };
      if (payload.detail !== undefined) {
        detail = formatApiDetail(payload.detail);
      }
    } catch {
      // JSON değilse statusText kullan.
    }
    throw new ApiError(`API isteği başarısız (${response.status})`, response.status, detail);
  }
  return response.json() as Promise<T>;
}

async function apiFetch<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    ...init,
    cache: "no-store",
    headers: buildClientHeaders(init?.headers),
  });
  return parseResponse<T>(response);
}

/** @deprecated Auth artık BFF'de; istemci header'ı secret taşımaz. */
function buildAuthHeaders(extra?: HeadersInit): HeadersInit {
  return buildClientHeaders(extra);
}

export { apiFetch, buildAuthHeaders, parseResponse };
