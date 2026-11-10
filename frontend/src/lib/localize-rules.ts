/** Pipeline/dashboard kural metinlerini locale katalogundan yeniden yazar. */

export type RuleLike = {
  rule_id?: string;
  message?: string;
  action?: string;
  severity?: string;
};

type TranslateFn = (key: string, params?: Record<string, string | number>) => string;

const KNOWN_RULE_IDS = new Set([
  "critical_risk",
  "elevated_risk",
  "high_mape",
  "high_imbalance_cost",
  "nominal_operations",
]);

export function isSimulationRule(rule: RuleLike, scadaIsMock = false): boolean {
  if (scadaIsMock) return true;
  const msg = `${rule.message ?? ""} ${rule.action ?? ""}`.toLowerCase();
  return (
    msg.includes("simülasyon") ||
    msg.includes("simulation") ||
    msg.includes("proxy") ||
    msg.includes("mock")
  );
}

export function localizeRule(
  t: TranslateFn,
  rule: RuleLike,
  scadaIsMock = false,
): { message: string; action: string } {
  const id = rule.rule_id && KNOWN_RULE_IDS.has(rule.rule_id) ? rule.rule_id : "nominal_operations";
  const variant = isSimulationRule(rule, scadaIsMock) ? "sim" : "live";
  const messageKey = `rules.${id}.${variant}.message`;
  const actionKey = `rules.${id}.${variant}.action`;
  const message = t(messageKey);
  const action = t(actionKey);
  return {
    message: message === messageKey ? (rule.message ?? "") : message,
    action: action === actionKey ? (rule.action ?? "") : action,
  };
}
