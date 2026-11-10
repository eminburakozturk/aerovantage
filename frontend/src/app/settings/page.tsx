"use client";

import { useCallback, useEffect, useState, Suspense } from "react";

import { LanguageSettingsPanel } from "@/components/settings/language-settings";
import { OpsPageHeader } from "@/components/ops/ops-page-header";
import { OpsPanel } from "@/components/ops/ops-panel";
import { StatusIndicator } from "@/components/ops/status-indicator";
import { EmptyState, ErrorBanner, LoadingBlock, PageLoading } from "@/components/ui/async-state";
import { useWorkspaceTab, WorkspaceTabs } from "@/components/workspace/workspace-tabs";
import { useOperasyon } from "@/context/operasyon-context";
import { useTranslations } from "@/context/locale-context";
import { useWorkspace, WORKSPACE_IDS } from "@/hooks/use-workspaces";
import { useUserMessages } from "@/lib/user-messages";
import {
  fetchAiModels,
  fetchHealth,
  fetchSystemConfig,
  fetchUsers,
  type AiModelsResponse,
  type HealthResponse,
  type PlatformUser,
  type SystemConfigResponse,
} from "@/lib/api";
import { getDefaultTab, resolveWorkspaceTab } from "@/lib/workspace-config";

function SettingsInner() {
  const tab = useWorkspaceTab(WORKSPACE_IDS.settings, getDefaultTab(WORKSPACE_IDS.settings));
  const workspace = useWorkspace(WORKSPACE_IDS.settings);
  const { t } = useTranslations("settings");
  const { getErrorMessage } = useUserMessages();
  const { assets, assetsError } = useOperasyon();
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [users, setUsers] = useState<PlatformUser[]>([]);
  const [models, setModels] = useState<AiModelsResponse | null>(null);
  const [config, setConfig] = useState<SystemConfigResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [h, u, m, c] = await Promise.all([
        fetchHealth(),
        fetchUsers(),
        fetchAiModels(),
        fetchSystemConfig(),
      ]);
      setHealth(h);
      setUsers(u);
      setModels(m);
      setConfig(c);
    } catch (err) {
      setError(getErrorMessage(err, t("loadFailed")));
    } finally {
      setLoading(false);
    }
  }, [getErrorMessage, t]);

  useEffect(() => {
    void load();
  }, [load]);

  const validTab = resolveWorkspaceTab(workspace, tab);

  return (
    <div className="flex h-full min-h-0 items-stretch overflow-hidden">
      <div className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden">
        <OpsPageHeader section={workspace.section} title={workspace.title} description={workspace.description} />
        <WorkspaceTabs tabs={workspace.tabs} activeTab={validTab} basePath={workspace.href} />
        <div className="min-h-0 flex-1 overflow-y-auto p-2">
          {error ? <ErrorBanner message={error} onRetry={() => void load()} className="mb-2" /> : null}

          {loading && validTab !== "overview" && validTab !== "language" ? (
            <LoadingBlock rows={3} className="mb-2" />
          ) : null}

          {validTab === "language" ? <LanguageSettingsPanel /> : null}

          {validTab === "users" ? (
            <OpsPanel title={t("users.title")} meta={t("users.meta", { count: users.length })}>
              <table className="w-full text-[10px]">
                <thead>
                  <tr className="border-b border-[#27272A] text-left text-zinc-600">
                    <th className="pb-2 pr-3">{t("users.name")}</th>
                    <th className="pb-2 pr-3">{t("users.email")}</th>
                    <th className="pb-2 pr-3">{t("users.role")}</th>
                    <th className="pb-2">{t("users.status")}</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((u) => (
                    <tr key={u.id} className="ops-row-hover border-b border-[#27272A]/50">
                      <td className="py-2 pr-3 text-zinc-200">{u.name}</td>
                      <td className="py-2 pr-3 text-zinc-500">{u.email}</td>
                      <td className="py-2 pr-3 text-zinc-400">{u.role}</td>
                      <td className="py-2 text-zinc-300">{u.status}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </OpsPanel>
          ) : null}

          {validTab === "models" ? (
            models ? (
              <OpsPanel
                title={t("models.title")}
                meta={models.live_ready ? t("models.modeLive") : t("models.modePlaybook")}
              >
                <StatusIndicator
                  status={models.live_ready ? "ok" : "warn"}
                  label={models.live_ready ? t("models.modeLive") : t("models.modePlaybook")}
                />
                <p className="mt-3 text-[11px] text-zinc-300">
                  {t("models.active", { name: models.active_model.name, type: models.active_model.type })}
                </p>
                <p className="mt-2 text-[10px] text-zinc-600">
                  {t("models.apiKey", {
                    status: models.api_key_configured
                      ? t("models.apiKeyConfigured")
                      : t("models.apiKeyMissing"),
                  })}
                </p>
                <p className="mt-1 text-[10px] text-zinc-600">
                  {t("models.providers", { list: models.available_providers.join(", ") })}
                </p>
                {models.playbook_entries != null ? (
                  <p className="mt-1 text-[10px] text-zinc-600">
                    {t("models.playbookEntries", { count: models.playbook_entries })}
                  </p>
                ) : null}
                {!models.live_ready ? (
                  <p className="mt-3 border border-amber-500/30 bg-amber-500/5 px-2 py-2 text-[10px] text-amber-200/90">
                    {t("models.cutoverHint")}
                  </p>
                ) : null}
                <p className="mt-2 text-[10px] text-zinc-600">{t("models.docsHint")}</p>
              </OpsPanel>
            ) : (
              <OpsPanel title={t("models.title")} meta={t("models.loading")}>
                <p className="text-[10px] text-zinc-600">
                  {loading ? t("models.loadingInfo") : t("models.loadFailed")}
                </p>
              </OpsPanel>
            )
          ) : null}

          {validTab === "config" ? (
            config ? (
              <OpsPanel title={t("config.title")} meta={config.app_env}>
                <dl className="space-y-1 text-[10px]">
                  <Row label={t("config.env")} value={config.app_env} />
                  <Row label={t("config.log")} value={config.log_level} />
                  <Row
                    label={t("config.epiasMode")}
                    value={config.epias_use_mock ? t("config.testMode") : t("config.liveMode")}
                  />
                  <Row
                    label={t("config.weatherMode")}
                    value={config.weather_use_mock ? t("config.testMode") : t("config.liveMode")}
                  />
                  <Row
                    label={t("config.scadaMode")}
                    value={config.scada_use_mock ? t("config.testMode") : t("config.liveMode")}
                  />
                  <Row label={t("config.llm")} value={config.llm_provider} />
                </dl>
              </OpsPanel>
            ) : (
              <EmptyState
                title={t("config.loadFailedTitle")}
                message={loading ? t("config.loading") : t("config.unavailable")}
              />
            )
          ) : null}

          {validTab === "overview" ? (
            <div className="grid gap-2 lg:grid-cols-2">
              <OpsPanel title={t("overview.apiTitle")}>
                <StatusIndicator
                  status={loading ? "idle" : health?.status === "ok" ? "ok" : "warn"}
                  label={health?.status === "ok" ? t("overview.apiOk") : t("overview.apiWarn")}
                />
                {health?.data_hub ? (
                  <ul className="mt-3 space-y-1">
                    {Object.entries(health.data_hub).map(([name, hub]) => (
                      <li
                        key={name}
                        className="flex items-center justify-between text-[10px] text-zinc-400"
                      >
                        <span className="font-medium text-zinc-300">{name}</span>
                        <span
                          className={
                            hub.mode === "live" && hub.status === "ok"
                              ? "font-mono text-zinc-400"
                              : "font-mono text-amber-400"
                          }
                        >
                          {hub.label || hub.mode || hub.status}
                        </span>
                      </li>
                    ))}
                  </ul>
                ) : null}
              </OpsPanel>
              <OpsPanel title={t("overview.plantsTitle")} meta={t("overview.plantsMeta", { count: assets.length })}>
                {assetsError ? <p className="text-[10px] text-rose-300">{assetsError}</p> : null}
                {assets.map((a) => (
                  <p key={a.id} className="text-[10px] text-zinc-400">
                    {a.name} · {a.capacity_mw} MW
                  </p>
                ))}
              </OpsPanel>
              <LanguageSettingsPanel />
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}

export default function SettingsPage() {
  const { t } = useTranslations("async");

  return (
    <Suspense fallback={<PageLoading label={t("settingsLoading")} />}>
      <SettingsInner />
    </Suspense>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between border-b border-[#27272A] py-1">
      <dt className="text-zinc-600">{label}</dt>
      <dd className="font-mono text-zinc-400">{value}</dd>
    </div>
  );
}
