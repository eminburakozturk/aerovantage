"use client";

import { useCallback, useEffect, useState } from "react";

import { KpiCell } from "@/components/ops/kpi-cell";
import { OpsPanel } from "@/components/ops/ops-panel";
import { Button } from "@/components/ui/button";
import { useOperasyon } from "@/context/operasyon-context";
import { useTranslations } from "@/context/locale-context";
import {
  fetchScenarioHistory,
  runScenario,
  type ScenarioResult,
} from "@/lib/api";
import { ErrorBanner } from "@/components/ui/async-state";
import { getErrorMessage } from "@/lib/user-messages";

interface ScenariosWorkspaceProps {
  tab: string;
}

export function ScenariosWorkspace({ tab }: ScenariosWorkspaceProps) {
  const { selectedAssetId } = useOperasyon();
  const { t, bcp47, locale } = useTranslations("ui");
  const [history, setHistory] = useState<ScenarioResult[]>([]);
  const [result, setResult] = useState<ScenarioResult | null>(null);
  const [windAdj, setWindAdj] = useState(0);
  const [ptfAdj, setPtfAdj] = useState(0);
  const [turbinesDown, setTurbinesDown] = useState(0);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadHistory = useCallback(async () => {
    try {
      setHistory(await fetchScenarioHistory(15, locale));
    } catch {
      setHistory([]);
    }
  }, [locale]);

  useEffect(() => {
    void loadHistory();
  }, [loadHistory]);

  const handleRun = async () => {
    if (!selectedAssetId) return;
    setRunning(true);
    setError(null);
    try {
      const res = await runScenario(
        {
          asset_id: selectedAssetId,
          wind_adjustment_pct: windAdj,
          ptf_adjustment_pct: ptfAdj,
          turbines_down: turbinesDown,
        },
        locale,
      );
      setResult(res);
      await loadHistory();
    } catch (err) {
      setError(getErrorMessage(err, t("scenarios.noScenario")));
    } finally {
      setRunning(false);
    }
  };

  if (tab === "history") {
    return (
      <OpsPanel title={t("scenarios.scenarioHistory")} meta={t("commonUi.recordsMeta", { count: history.length })}>
          <div className="space-y-2">
            {history.map((entry) => (
              <div key={entry.scenario_id} className="border border-[#27272A] p-2">
                <p className="font-mono text-[9px] text-zinc-600">{entry.generated_at}</p>
                <p className="mt-1 text-[10px] text-zinc-400">{entry.summary}</p>
              </div>
            ))}
            {history.length === 0 ? <p className="text-[10px] text-zinc-600">{t("scenarios.noScenario")}</p> : null}
          </div>
        </OpsPanel>
    );
  }

  return (
    <div className="space-y-2">
      {error ? <ErrorBanner message={error} className="mb-2" /> : null}

      <OpsPanel title={t("scenarios.scenarioParamsTitle")} meta={selectedAssetId || t("assets.selectPlant")}>
        <div className="grid gap-3 sm:grid-cols-3">
          <SliderField label={t("scenarios.windChange")} value={windAdj} min={-30} max={30} unit="%" onChange={setWindAdj} />
          <SliderField label={t("scenarios.ptfChange")} value={ptfAdj} min={-20} max={20} unit="%" onChange={setPtfAdj} />
          <SliderField label={t("scenarios.turbineFailure")} value={turbinesDown} min={0} max={5} unit={t("commonUi.unitCount")} onChange={setTurbinesDown} />
        </div>
        <Button
          type="button"
          onClick={() => void handleRun()}
          disabled={running || !selectedAssetId}
          className="mt-3 h-8 rounded-none bg-[#3B82F6] text-[11px] hover:bg-[#2563EB]"
        >
          {running ? t("scenarios.running") : t("scenarios.runScenario")}
        </Button>
      </OpsPanel>

      {result ? (
        <>
          <section className="grid grid-cols-2 border border-[#27272A] bg-[#18181B] md:grid-cols-4">
            <KpiCell label={t("scenarios.baselineForecast")} value={result.baseline_forecast_mw.toFixed(1)} unit="MW" />
            <KpiCell label={t("scenarios.scenarioForecast")} value={result.adjusted_forecast_mw.toFixed(1)} unit="MW" status="neutral" />
            <KpiCell label={t("scenarios.baselineCost")} value={result.baseline_cost_tl.toLocaleString(bcp47)} unit="TL" />
            <KpiCell label={t("scenarios.scenarioCost")} value={result.adjusted_cost_tl.toLocaleString(bcp47)} unit="TL" status="neutral" />
          </section>
          <OpsPanel title={t("scenarios.resultSummary")} meta={t("scenarios.riskChangeMeta", { baseline: result.baseline_risk_score, adjusted: result.adjusted_risk_score })}>
            <p className="text-[11px] text-zinc-300">{result.summary}</p>
          </OpsPanel>
        </>
      ) : null}
    </div>
  );
}

function SliderField({
  label,
  value,
  min,
  max,
  unit,
  onChange,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  unit: string;
  onChange: (v: number) => void;
}) {
  return (
    <div>
      <label className="text-[10px] text-zinc-500">{label}</label>
      <input
        type="range"
        min={min}
        max={max}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="mt-1 w-full"
      />
      <p className="font-mono text-[11px] text-zinc-300">
        {value > 0 ? "+" : ""}
        {value} {unit}
      </p>
    </div>
  );
}
