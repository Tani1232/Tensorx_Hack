"""
risk_engine.py
--------------
Core orchestrator: ties together feature engineering, hard-decline rules,
weighted score calculation, fraud detection, reason code generation,
and audit persistence.

Entry point: score_application(input_data: dict) → dict
"""

from typing import List, Tuple, Dict

from models import (
    LoanApplicationInput,
    ComputedFeatures,
    HardDeclineResult,
    RiskScoreOutput,
    AuditRecord,
    RiskBand,
    Decision,
)
from feature_engineering import engineer_features
from rules_engine import evaluate_hard_rules
from database import save_audit_record
from config import (
    SCORE_WEIGHTS,
    RISK_BAND_LOW_MIN,
    RISK_BAND_MEDIUM_MIN,
    RISK_BAND_HIGH_MIN,
    FRAUD_GEO_MISMATCH_CODE,
    FRAUD_MULTIPLE_APPS_CODE,
    FRAUD_HIGH_ENQUIRY_CODE,
    HIGH_ENQUIRY_THRESHOLD,
    NONE_FLAG,
)
from utils import (
    generate_application_id,
    utc_now_iso,
    to_serialisable,
    generate_explanation,
    logger,
    clamp,
)


# ──────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────

def score_application(input_data: dict) -> dict:
    """
    End-to-end risk scoring pipeline.

    Pipeline:
    1. Validate & parse input (Pydantic)
    2. Engineer features (EMI, FOIR, normalised scores)
    3. Evaluate hard-decline rules (policy override)
    4. Compute weighted risk score
    5. Determine risk band + decision
    6. Build fraud flags
    7. Generate reason codes
    8. Build natural language explanation
    9. Persist to MongoDB (audit trail)
    10. Return structured output

    Args:
        input_data: Raw dict matching LoanApplicationInput schema.

    Returns:
        Serialisable dict matching RiskScoreOutput schema.
    """
    app_id = generate_application_id()
    ts     = utc_now_iso()
    logger.info("─" * 60)
    logger.info("Processing application: %s", app_id)

    # ── 1. Parse & Validate ─────────────────────────
    app = LoanApplicationInput(**input_data)

    # ── 2. Feature Engineering ──────────────────────
    features = engineer_features(app)

    # ── 3. Hard Decline Rules ───────────────────────
    decline_result = evaluate_hard_rules(app, features)

    if decline_result.is_declined:
        output = _build_decline_output(features, decline_result, app)
    else:
        # ── 4. Weighted Score ────────────────────────
        raw_score, factor_scores = _compute_weighted_score(features)
        risk_score = int(round(raw_score))

        # ── 5. Risk Band + Decision ──────────────────
        risk_band, decision = _classify(risk_score)

        # ── 6. Fraud Flags ───────────────────────────
        flags = _collect_fraud_flags(app)

        # Override decision to REVIEW if active fraud signals
        if flags and flags != [NONE_FLAG] and decision == Decision.APPROVE:
            decision = Decision.REVIEW
            logger.warning("Decision overridden to REVIEW due to fraud flags: %s", flags)

        # ── 7. Reason Codes ──────────────────────────
        reason_codes = _generate_reason_codes(app, features)
        top_factors  = _top_factors(factor_scores)

        # ── 8. Explanation ───────────────────────────
        explanation = generate_explanation(
            decision=decision.value,
            risk_band=risk_band.value,
            reason_codes=reason_codes,
            flags=flags,
        )

        output = RiskScoreOutput(
            risk_score=risk_score,
            risk_band=risk_band.value,
            decision=decision.value,
            foir=round(features.foir, 4),
            flags=flags,
            reason_codes=reason_codes,
            top_factors=top_factors,
            llm_explanation=explanation,
        )

    # ── 9. Audit Persistence ─────────────────────────
    audit = AuditRecord(
        application_id=app_id,
        timestamp=ts,
        input_data=to_serialisable(app),
        computed_features=to_serialisable(features),
        hard_decline_result=to_serialisable(decline_result),
        output=to_serialisable(output),
    )
    save_audit_record(audit.dict())

    logger.info(
        "Result → score=%s band=%s decision=%s",
        output.risk_score, output.risk_band, output.decision,
    )
    logger.info("─" * 60)

    return to_serialisable(output)


# ──────────────────────────────────────────────
# Private Helpers
# ──────────────────────────────────────────────

def _compute_weighted_score(
    features: ComputedFeatures,
) -> Tuple[float, Dict[str, float]]:
    """
    Apply weight vector to normalised feature scores.

    Returns:
        (weighted_total_0_1000, dict of per-factor weighted contributions)
    """
    factor_map: Dict[str, float] = {
        "cibil":               features.normalized_cibil,
        "foir":                features.normalized_foir,
        "dpd":                 features.normalized_dpd,
        "credit_utilization":  features.normalized_utilization,
        "enquiry":             features.normalized_enquiry,
        "employment_tenure":   features.normalized_tenure,
        "income_verification": features.normalized_income_verification,
    }

    weighted: Dict[str, float] = {}
    total = 0.0
    for factor, raw_score in factor_map.items():
        contribution = raw_score * SCORE_WEIGHTS[factor]
        weighted[factor] = round(contribution, 2)
        total += contribution

    return clamp(total, 0.0, 1000.0), weighted


def _classify(score: int) -> Tuple[RiskBand, Decision]:
    """Map numeric risk score to band and decision."""
    if score >= RISK_BAND_LOW_MIN:
        return RiskBand.LOW, Decision.APPROVE
    elif score >= RISK_BAND_MEDIUM_MIN:
        return RiskBand.MEDIUM, Decision.REDUCE
    elif score >= RISK_BAND_HIGH_MIN:
        return RiskBand.HIGH, Decision.REVIEW
    else:
        return RiskBand.VERY_HIGH, Decision.DECLINE


def _collect_fraud_flags(app: LoanApplicationInput) -> List[str]:
    """Evaluate fraud signals and return active flag codes."""
    flags: List[str] = []

    if app.fraud_signals.geo_mismatch:
        flags.append(FRAUD_GEO_MISMATCH_CODE)

    if app.fraud_signals.multiple_applications:
        flags.append(FRAUD_MULTIPLE_APPS_CODE)

    if app.bureau.enquiry_last_6_months > HIGH_ENQUIRY_THRESHOLD:
        flags.append(FRAUD_HIGH_ENQUIRY_CODE)

    return flags if flags else [NONE_FLAG]


def _generate_reason_codes(
    app: LoanApplicationInput,
    features: ComputedFeatures,
) -> List[str]:
    """
    Produce a list of human-readable reason codes that explain
    the positive and negative factors in the scoring.
    """
    codes: List[str] = []

    # ── CIBIL ─────────────────────────────────────
    if app.bureau.cibil_score >= 750:
        codes.append("GOOD_CIBIL")
    elif app.bureau.cibil_score >= 700:
        codes.append("AVERAGE_CIBIL")
    else:
        codes.append("WEAK_CIBIL")

    # ── FOIR ──────────────────────────────────────
    if features.foir_label == "GOOD":
        codes.append("LOW_FOIR")
    elif features.foir_label == "RISKY":
        codes.append("MODERATE_FOIR")
    else:
        codes.append("HIGH_FOIR")

    # ── DPD ───────────────────────────────────────
    if app.bureau.dpd_90_plus_count == 0:
        codes.append("NO_DPD")
    else:
        codes.append("DPD_PRESENT")

    # ── Credit Utilization ─────────────────────────
    if app.bureau.credit_utilization < 30:
        codes.append("LOW_CREDIT_UTILIZATION")
    elif app.bureau.credit_utilization >= 70:
        codes.append("HIGH_CREDIT_UTILIZATION")

    # ── Employment Tenure ──────────────────────────
    tenure = app.customer_profile.employment_tenure_months
    if tenure >= 24:
        codes.append("STABLE_EMPLOYMENT")
    elif tenure >= 12:
        codes.append("MODERATE_EMPLOYMENT")
    else:
        codes.append("SHORT_EMPLOYMENT")

    # ── Income Verification ────────────────────────
    if app.verification.income_match_percent >= 90:
        codes.append("INCOME_VERIFIED")
    else:
        codes.append("INCOME_MISMATCH")

    # ── Enquiries ─────────────────────────────────
    if app.bureau.enquiry_last_6_months <= 2:
        codes.append("LOW_ENQUIRIES")
    elif app.bureau.enquiry_last_6_months > HIGH_ENQUIRY_THRESHOLD:
        codes.append("HIGH_ENQUIRIES")

    # ── Credit History ─────────────────────────────
    if app.bureau.credit_history_months >= 36:
        codes.append("LONG_CREDIT_HISTORY")

    # ── Bureau Flags ──────────────────────────────
    if app.bureau.has_settled_accounts:
        codes.append("SETTLED_ACCOUNTS")

    if app.bureau.has_npa:
        codes.append("NPA_PRESENT")

    return codes


def _top_factors(factor_scores: Dict[str, float]) -> List[str]:
    """
    Return the top-3 factor names sorted by their weighted contribution.
    These represent the factors most influential in the final score.
    """
    sorted_factors = sorted(factor_scores.items(), key=lambda x: x[1], reverse=True)
    return [name for name, _ in sorted_factors[:3]]


def _build_decline_output(
    features: ComputedFeatures,
    decline_result: HardDeclineResult,
    app: LoanApplicationInput,
) -> RiskScoreOutput:
    """Build a RiskScoreOutput for hard-declined applications."""
    explanation = generate_explanation(
        decision="DECLINE",
        risk_band="VERY_HIGH",
        reason_codes=decline_result.triggered_rules,
        flags=[],
    )
    return RiskScoreOutput(
        risk_score=0,
        risk_band=RiskBand.VERY_HIGH.value,
        decision=Decision.DECLINE.value,
        foir=round(features.foir, 4),
        flags=[NONE_FLAG],
        reason_codes=decline_result.triggered_rules,
        top_factors=decline_result.triggered_rules[:3],
        llm_explanation=explanation,
    )
