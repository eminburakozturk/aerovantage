/** Kullanıcıya gösterilecek mesajlar — locale destekli */

"use client";

import { useCallback, useMemo } from "react";

import { useLocale, useTranslations } from "@/context/locale-context";
import { ApiError } from "@/lib/api";
import { translate, type MessageTree } from "@/i18n/get-message";
import { loadMessages } from "@/i18n/load-messages";
import { DEFAULT_LOCALE, normalizeLocale, type Locale } from "@/i18n/config";

const ERROR_PATTERN_KEYS: Array<{ test: RegExp; key: string }> = [
  { test: /failed to fetch|network|fetch|erisilemedi|ulaşılamadı/i, key: "patterns.network" },
  {
    test: /data quality gate|veri kalitesi gate|datenqualitaet|kalite gate|quality gate/i,
    key: "patterns.dataQualityGate",
  },
  {
    test: /model reliability gate|model güvenilirlik gate|modellzuverlaessigkeit/i,
    key: "patterns.modelReliabilityGate",
  },
  {
    test: /decision reliability gate|karar güvenilirlik gate|entscheidungszuverlaessigkeit/i,
    key: "patterns.decisionReliabilityGate",
  },
  { test: /422|unprocessable|validat/i, key: "patterns.validation" },
  { test: /401|unauthorized|authentifizierung/i, key: "patterns.unauthorized" },
  { test: /403|forbidden|erişim|zugriff/i, key: "patterns.forbidden" },
  { test: /404|not found|nicht gefunden/i, key: "patterns.notFound" },
  { test: /500|internal server/i, key: "patterns.server" },
  { test: /502|503|bad gateway|backend.*nicht/i, key: "patterns.gateway" },
  { test: /timeout|timed out|zeitueberschreitung/i, key: "patterns.timeout" },
  { test: /json|parse|verarbeiten/i, key: "patterns.parse" },
  { test: /boş dosya|empty file|leere datei/i, key: "downloadEmpty" },
];

function resolveLocale(): Locale {
  if (typeof window === "undefined") return DEFAULT_LOCALE;
  try {
    return normalizeLocale(window.localStorage.getItem("aerovantage.locale"));
  } catch {
    return DEFAULT_LOCALE;
  }
}

function translateErrorKey(key: string, locale?: Locale): string {
  const loc = locale ?? resolveLocale();
  const tree = loadMessages(loc).errors as MessageTree;
  return translate(tree, key);
}

function matchErrorPattern(raw: string, locale?: Locale): string {
  const text = raw.trim();
  if (!text) return translateErrorKey("generic", locale);
  for (const { test, key } of ERROR_PATTERN_KEYS) {
    if (test.test(text)) return translateErrorKey(key, locale);
  }
  if (text.length > 160) return translateErrorKey("long", locale);
  return text;
}

export function useUserMessages() {
  const { locale } = useLocale();
  const { t: te } = useTranslations("errors");
  const { t: tc } = useTranslations("common");

  const friendlyError = useCallback(
    (raw: string | null | undefined): string => matchErrorPattern(raw ?? "", locale),
    [locale],
  );

  const getErrorMessage = useCallback(
    (error: unknown, fallback?: string): string => {
      const resolvedFallback = fallback ?? te("generic");
      if (error instanceof ApiError) {
        const matched = matchErrorPattern(error.detail ?? error.message, locale);
        // Ham API metni locale'e çevrilebildiyse onu kullan
        if (matched !== (error.detail ?? error.message)) return matched;
        // Pattern yoksa ama gate ise fallback
        if (error.status === 422) return te("patterns.validation");
        return matched || resolvedFallback;
      }
      if (error instanceof Error) return matchErrorPattern(error.message, locale);
      return resolvedFallback;
    },
    [te, locale],
  );

  const statusLabel = useCallback(
    (value: string | undefined | null): string => {
      if (!value) return "—";
      const key = value.toLowerCase();
      const translated = tc(`status.${key}`);
      return translated === `status.${key}` ? value : translated;
    },
    [tc],
  );

  return useMemo(
    () => ({
      friendlyError,
      getErrorMessage,
      statusLabel,
    }),
    [friendlyError, getErrorMessage, statusLabel],
  );
}

/** Locale-aware — localStorage'daki dil ile çalışır (hook dışı). */
export function friendlyError(raw: string | null | undefined): string {
  return matchErrorPattern(raw ?? "");
}

/** Locale-aware — localStorage'daki dil ile çalışır (hook dışı). */
export function getErrorMessage(
  error: unknown,
  fallback?: string,
): string {
  const loc = resolveLocale();
  const resolvedFallback = fallback ?? translateErrorKey("generic", loc);
  if (error instanceof ApiError) {
    const source = error.detail ?? error.message;
    const matched = matchErrorPattern(source, loc);
    if (matched !== source) return matched;
    if (error.status === 422) return translateErrorKey("patterns.validation", loc);
    return matched || resolvedFallback;
  }
  if (error instanceof Error) return matchErrorPattern(error.message, loc);
  return resolvedFallback;
}

export function statusLabel(value: string | undefined | null): string {
  if (!value) return "—";
  const loc = resolveLocale();
  const tree = loadMessages(loc).common as MessageTree;
  const key = `status.${value.toLowerCase()}`;
  const translated = translate(tree, key);
  return translated === key ? value : translated;
}
