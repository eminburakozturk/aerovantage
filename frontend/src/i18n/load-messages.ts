import type { Locale } from "./config";

import deAsync from "@/locales/de/async.json";
import deCommon from "@/locales/de/common.json";
import deErrors from "@/locales/de/errors.json";
import deMonitoring from "@/locales/de/monitoring.json";
import deNav from "@/locales/de/nav.json";
import deSettings from "@/locales/de/settings.json";
import deTopbar from "@/locales/de/topbar.json";
import deUi from "@/locales/de/ui.json";
import deWorkspaces from "@/locales/de/workspaces.json";
import enAsync from "@/locales/en/async.json";
import enCommon from "@/locales/en/common.json";
import enErrors from "@/locales/en/errors.json";
import enMonitoring from "@/locales/en/monitoring.json";
import enNav from "@/locales/en/nav.json";
import enSettings from "@/locales/en/settings.json";
import enTopbar from "@/locales/en/topbar.json";
import enUi from "@/locales/en/ui.json";
import enWorkspaces from "@/locales/en/workspaces.json";
import trAsync from "@/locales/tr/async.json";
import trCommon from "@/locales/tr/common.json";
import trErrors from "@/locales/tr/errors.json";
import trMonitoring from "@/locales/tr/monitoring.json";
import trNav from "@/locales/tr/nav.json";
import trSettings from "@/locales/tr/settings.json";
import trTopbar from "@/locales/tr/topbar.json";
import trUi from "@/locales/tr/ui.json";
import trWorkspaces from "@/locales/tr/workspaces.json";

export type Messages = {
  common: typeof trCommon;
  nav: typeof trNav;
  workspaces: typeof trWorkspaces;
  errors: typeof trErrors;
  async: typeof trAsync;
  settings: typeof trSettings;
  topbar: typeof trTopbar;
  monitoring: typeof trMonitoring;
  ui: typeof trUi;
};

const MESSAGE_CATALOG: Record<Locale, Messages> = {
  tr: {
    common: trCommon,
    nav: trNav,
    workspaces: trWorkspaces,
    errors: trErrors,
    async: trAsync,
    settings: trSettings,
    topbar: trTopbar,
    monitoring: trMonitoring,
    ui: trUi,
  },
  en: {
    common: enCommon,
    nav: enNav,
    workspaces: enWorkspaces,
    errors: enErrors,
    async: enAsync,
    settings: enSettings,
    topbar: enTopbar,
    monitoring: enMonitoring,
    ui: enUi,
  },
  de: {
    common: deCommon,
    nav: deNav,
    workspaces: deWorkspaces,
    errors: deErrors,
    async: deAsync,
    settings: deSettings,
    topbar: deTopbar,
    monitoring: deMonitoring,
    ui: deUi,
  },
};

export function loadMessages(locale: Locale): Messages {
  return MESSAGE_CATALOG[locale];
}
