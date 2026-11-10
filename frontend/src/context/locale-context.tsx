"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import {
  DEFAULT_LOCALE,
  LOCALE_BCP47,
  LOCALE_STORAGE_KEY,
  type Locale,
  normalizeLocale,
} from "@/i18n/config";
import { translate, type MessageTree } from "@/i18n/get-message";
import { loadMessages, type Messages } from "@/i18n/load-messages";

type TranslateFn = (key: string, params?: Record<string, string | number>) => string;

interface LocaleContextValue {
  locale: Locale;
  /** false until localStorage locale is applied — gate API fetches to avoid TR→EN races */
  localeReady: boolean;
  setLocale: (locale: Locale) => void;
  messages: Messages;
  t: TranslateFn;
  bcp47: string;
}

const LocaleContext = createContext<LocaleContextValue | null>(null);

function readStoredLocale(): Locale {
  if (typeof window === "undefined") return DEFAULT_LOCALE;
  return normalizeLocale(window.localStorage.getItem(LOCALE_STORAGE_KEY));
}

export function LocaleProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>(DEFAULT_LOCALE);
  const [localeReady, setLocaleReady] = useState(false);

  useEffect(() => {
    setLocaleState(readStoredLocale());
    setLocaleReady(true);
  }, []);

  const setLocale = useCallback((next: Locale) => {
    setLocaleState(next);
    if (typeof window !== "undefined") {
      window.localStorage.setItem(LOCALE_STORAGE_KEY, next);
      document.documentElement.lang = next;
    }
  }, []);

  useEffect(() => {
    if (!localeReady) return;
    document.documentElement.lang = locale;
  }, [locale, localeReady]);

  const messages = useMemo(() => loadMessages(locale), [locale]);

  const t = useCallback<TranslateFn>(
    (key, params) => {
      const [namespace, ...rest] = key.split(".");
      const namespaceMessages = messages[namespace as keyof Messages];
      if (!namespaceMessages) return key;
      return translate(namespaceMessages as MessageTree, rest.join("."), params);
    },
    [messages],
  );

  const value = useMemo(
    () => ({
      locale,
      localeReady,
      setLocale,
      messages,
      t,
      bcp47: LOCALE_BCP47[locale],
    }),
    [locale, localeReady, setLocale, messages, t],
  );

  return <LocaleContext.Provider value={value}>{children}</LocaleContext.Provider>;
}

export function useLocale() {
  const context = useContext(LocaleContext);
  if (!context) {
    throw new Error("useLocale must be used within LocaleProvider");
  }
  return context;
}

export function useTranslations(namespace?: keyof Messages) {
  const { t, locale, localeReady, setLocale, bcp47, messages } = useLocale();
  const scoped = useCallback<TranslateFn>(
    (key, params) => t(namespace ? `${namespace}.${key}` : key, params),
    [namespace, t],
  );
  return { t: scoped, locale, localeReady, setLocale, bcp47, messages };
}
