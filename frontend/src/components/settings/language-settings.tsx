"use client";

import { LOCALE_LABELS, LOCALES } from "@/i18n/config";
import { useLocale, useTranslations } from "@/context/locale-context";
import { OpsPanel } from "@/components/ops/ops-panel";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export function LanguageSettingsPanel() {
  const { locale, setLocale } = useLocale();
  const { t } = useTranslations("settings");

  const onSelect = (code: typeof locale) => {
    setLocale(code);
    // Diğer sayfalar locale effect ile yenilenir; anında feedback
    if (typeof window !== "undefined") {
      window.dispatchEvent(new CustomEvent("aerovantage:locale-changed", { detail: code }));
    }
  };

  return (
    <OpsPanel title={t("language.title")} meta={LOCALE_LABELS[locale]}>
      <p className="mb-3 text-[11px] leading-relaxed text-zinc-500">{t("language.description")}</p>
      <p className="mb-2 text-[10px] text-zinc-600">
        {t("language.current")}: <span className="text-zinc-300">{LOCALE_LABELS[locale]}</span>
      </p>
      <div className="flex flex-wrap gap-2">
        {LOCALES.map((code) => (
          <Button
            key={code}
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => onSelect(code)}
            className={cn(
              "h-8 rounded-none border px-3 text-[10px]",
              locale === code
                ? "border-[#3B82F6] bg-[#18181B] text-zinc-100"
                : "border-[#27272A] text-zinc-400 hover:bg-[#141416]",
            )}
          >
            {LOCALE_LABELS[code]}
          </Button>
        ))}
      </div>
      <p className="mt-3 text-[10px] text-emerald-400/80">{t("language.saved")}</p>
    </OpsPanel>
  );
}
