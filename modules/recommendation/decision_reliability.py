"""FAZ 4 — decision reliability gate ve operational intelligence doğrulama."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from modules.ai.assistant import AIDecisionAssistant
from modules.ai.schemas import AIResponse
from modules.alerting.quality import ALERT_QUALITY_VERSION
from modules.forecast.production.explainability import EXPLAINABILITY_VERSION
from modules.recommendation.causality import CAUSALITY_VERSION
from modules.recommendation.quality import RECOMMENDATION_QUALITY_VERSION
from modules.risk.schemas import DailyRiskScoreResponse
from modules.risk.scoring import verify_risk_score_response

DECISION_RELIABILITY_VERSION = "1.0.0"
_HIGH_RISK_SCORE = 50
_HIGH_IMBALANCE_COST_TL = 3_000.0


@dataclass(frozen=True)
class DecisionReliabilityCheck:
    name: str
    category: str
    passed: bool
    message: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class DecisionReliabilityReport:
    gate_passed: bool
    checks: list[DecisionReliabilityCheck] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": DECISION_RELIABILITY_VERSION,
            "gate_passed": self.gate_passed,
            "checks": [
                {
                    "name": check.name,
                    "category": check.category,
                    "passed": check.passed,
                    "message": check.message,
                    "details": check.details,
                }
                for check in self.checks
            ],
        }


def merge_decision_reliability_reports(
    *reports: DecisionReliabilityReport,
) -> DecisionReliabilityReport:
    checks: list[DecisionReliabilityCheck] = []
    for report in reports:
        checks.extend(report.checks)
    gate_passed = all(report.gate_passed for report in reports)
    return DecisionReliabilityReport(gate_passed=gate_passed, checks=checks)


class DecisionReliabilityGateError(RuntimeError):
    """Decision reliability gate başarısız olduğu için pipeline durduruldu."""

    def __init__(self, report: DecisionReliabilityReport) -> None:
        self.report = report
        super().__init__("Decision reliability gate failed")


def run_decision_reliability_gate(
    *,
    risk_data: dict[str, Any],
    risk_response: DailyRiskScoreResponse | None,
    ai_response: AIResponse,
    model_attribution: dict[str, Any] | None,
    model_info: dict[str, Any],
    recommendation_quality: dict[str, Any] | None = None,
    alert_quality: dict[str, Any] | None = None,
    decision_causality: dict[str, Any] | None = None,
    strict_playbook: bool = False,
) -> DecisionReliabilityReport:
    """AI kararlarının model çıktıları ve operasyon metrikleriyle uyumunu doğrular."""
    checks = [
        _check_risk_score_verification(risk_response),
        _check_recommendation_consistency(risk_data, ai_response.action_plan, strict_playbook),
        _check_explainability_alignment(model_attribution, model_info),
        _check_ai_output_present(ai_response),
        _check_recommendation_quality_contract(recommendation_quality),
        _check_alert_quality_contract(alert_quality),
        _check_false_positive_rate(alert_quality),
        _check_false_negative_analysis(alert_quality),
        _check_decision_causality_contract(decision_causality),
    ]
    gate_passed = all(check.passed for check in checks)
    return DecisionReliabilityReport(gate_passed=gate_passed, checks=checks)


def enforce_decision_reliability_gate(report: DecisionReliabilityReport) -> DecisionReliabilityReport:
    if not report.gate_passed:
        raise DecisionReliabilityGateError(report)
    return report


def is_action_risk_aligned(risk_data: dict[str, Any], action_plan: str) -> bool:
    """Aksiyon planının risk seviyesiyle tutarlı olup olmadığını kontrol eder."""
    risk_score = int(risk_data.get("risk_score") or 0)
    total_cost = float(risk_data.get("total_imbalance_cost_tl") or 0.0)
    normalized = action_plan.strip().lower()
    if not normalized:
        return False
    if risk_score > _HIGH_RISK_SCORE or total_cost > _HIGH_IMBALANCE_COST_TL:
        return "standart izleme" not in normalized
    return True


def _check_risk_score_verification(risk_response: DailyRiskScoreResponse | None) -> DecisionReliabilityCheck:
    if risk_response is None:
        return DecisionReliabilityCheck(
            name="risk_score_verification",
            category="risk",
            passed=False,
            message="Risk yanıtı eksik",
        )
    verification = verify_risk_score_response(risk_response)
    return DecisionReliabilityCheck(
        name="risk_score_verification",
        category="risk",
        passed=bool(verification["passed"]),
        message="Risk skoru doğrulandı" if verification["passed"] else "Risk skoru tutarsız",
        details=verification,
    )


def _check_recommendation_consistency(
    risk_data: dict[str, Any],
    action_plan: str,
    strict_playbook: bool,
) -> DecisionReliabilityCheck:
    assistant = AIDecisionAssistant()
    expected = assistant.resolve_playbook_action_plan(risk_data)
    exact_match = action_plan.strip() == expected
    aligned = is_action_risk_aligned(risk_data, action_plan)
    passed = exact_match if strict_playbook else (exact_match or aligned)
    return DecisionReliabilityCheck(
        name="recommendation_consistency",
        category="recommendation",
        passed=passed,
        message="Recommendation tutarlı" if passed else "Recommendation risk ile uyumsuz",
        details={
            "expected_action_plan": expected,
            "actual_action_plan": action_plan,
            "exact_match": exact_match,
            "risk_aligned": aligned,
            "strict_playbook": strict_playbook,
        },
    )


def _check_explainability_alignment(
    model_attribution: dict[str, Any] | None,
    model_info: dict[str, Any],
) -> DecisionReliabilityCheck:
    model_type = str(model_info.get("type", "unknown"))
    if model_attribution is None:
        passed = model_type == "physics_only"
        return DecisionReliabilityCheck(
            name="explainability_alignment",
            category="explainability",
            passed=passed,
            message="Attribution mevcut" if passed else "Attribution eksik",
            details={"model_type": model_type},
        )

    method = str(model_attribution.get("method") or "")
    features = model_attribution.get("features") or []
    version_ok = model_attribution.get("version") == EXPLAINABILITY_VERSION
    method_ok = method in {"xgboost_tree_shap", "physics_only"}
    if model_type == "hybrid_xgb" and model_info.get("trained_samples", 0) > 0:
        method_ok = method == "xgboost_tree_shap" or (method == "physics_only" and not model_info.get("validation", {}).get("deployable"))
    passed = version_ok and method_ok and len(features) >= 1
    return DecisionReliabilityCheck(
        name="explainability_alignment",
        category="explainability",
        passed=passed,
        message="SHAP attribution model ile uyumlu" if passed else "Explainability uyumsuz",
        details={
            "model_type": model_type,
            "method": method,
            "feature_count": len(features),
            "version": model_attribution.get("version"),
        },
    )


def _check_ai_output_present(ai_response: AIResponse) -> DecisionReliabilityCheck:
    passed = bool(ai_response.insight.strip()) and bool(ai_response.action_plan.strip())
    return DecisionReliabilityCheck(
        name="ai_output_present",
        category="recommendation",
        passed=passed,
        message="AI çıktısı tam" if passed else "AI insight/action_plan eksik",
    )


def _check_recommendation_quality_contract(
    recommendation_quality: dict[str, Any] | None,
) -> DecisionReliabilityCheck:
    if recommendation_quality is None:
        return DecisionReliabilityCheck(
            name="recommendation_quality_contract",
            category="recommendation",
            passed=True,
            message="Recommendation quality henüz hesaplanmadı",
            details={"skipped": True},
        )
    required = (
        "version",
        "quality_score",
        "action_coverage",
        "improved_after_action_ratio",
        "reportable",
    )
    missing = [field for field in required if field not in recommendation_quality]
    passed = not missing and recommendation_quality.get("version") == RECOMMENDATION_QUALITY_VERSION
    return DecisionReliabilityCheck(
        name="recommendation_quality_contract",
        category="recommendation",
        passed=passed,
        message="Recommendation quality contract geçerli" if passed else "Recommendation quality eksik",
        details={"missing_fields": missing},
    )


def _check_alert_quality_contract(alert_quality: dict[str, Any] | None) -> DecisionReliabilityCheck:
    if alert_quality is None:
        return DecisionReliabilityCheck(
            name="alert_quality_contract",
            category="alert",
            passed=True,
            message="Alert quality henüz hesaplanmadı",
            details={"skipped": True},
        )
    required = (
        "version",
        "precision_proxy",
        "false_positive_rate",
        "false_negative_rate",
        "quality_score",
        "reportable",
    )
    missing = [field for field in required if field not in alert_quality]
    passed = not missing and alert_quality.get("version") == ALERT_QUALITY_VERSION
    return DecisionReliabilityCheck(
        name="alert_quality_contract",
        category="alert",
        passed=passed,
        message="Alert quality contract geçerli" if passed else "Alert quality eksik",
        details={"missing_fields": missing},
    )


def _check_false_positive_rate(alert_quality: dict[str, Any] | None) -> DecisionReliabilityCheck:
    if alert_quality is None:
        return DecisionReliabilityCheck(
            name="false_positive_rate",
            category="alert",
            passed=True,
            message="FP oranı henüz hesaplanmadı",
            details={"skipped": True},
        )
    rate = float(alert_quality.get("false_positive_rate", 0.0))
    passed = 0.0 <= rate <= 1.0
    return DecisionReliabilityCheck(
        name="false_positive_rate",
        category="alert",
        passed=passed,
        message="False positive oranı geçerli" if passed else "False positive oranı hatalı",
        details={"false_positive_rate": rate},
    )


def _check_false_negative_analysis(alert_quality: dict[str, Any] | None) -> DecisionReliabilityCheck:
    if alert_quality is None:
        return DecisionReliabilityCheck(
            name="false_negative_analysis",
            category="alert",
            passed=True,
            message="FN analizi henüz hesaplanmadı",
            details={"skipped": True},
        )
    rate = float(alert_quality.get("false_negative_rate", 0.0))
    proxy = int(alert_quality.get("false_negative_proxy", 0))
    passed = 0.0 <= rate <= 1.0 and proxy >= 0
    return DecisionReliabilityCheck(
        name="false_negative_analysis",
        category="alert",
        passed=passed,
        message="False negative analizi geçerli" if passed else "False negative analizi hatalı",
        details={
            "false_negative_rate": rate,
            "false_negative_proxy": proxy,
            "alert_opportunities": alert_quality.get("alert_opportunities"),
        },
    )


def _check_decision_causality_contract(
    decision_causality: dict[str, Any] | None,
) -> DecisionReliabilityCheck:
    if decision_causality is None:
        return DecisionReliabilityCheck(
            name="decision_causality_contract",
            category="causality",
            passed=True,
            message="Causality henüz hesaplanmadı",
            details={"skipped": True},
        )
    required = (
        "version",
        "causality_lift",
        "causality_signal",
        "action_pairs",
        "control_pairs",
        "reportable",
    )
    missing = [field for field in required if field not in decision_causality]
    passed = not missing and decision_causality.get("version") == CAUSALITY_VERSION
    return DecisionReliabilityCheck(
        name="decision_causality_contract",
        category="causality",
        passed=passed,
        message="Decision causality contract geçerli" if passed else "Causality contract eksik",
        details={"missing_fields": missing},
    )
