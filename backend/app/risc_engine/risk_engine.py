"""
risk_engine.py
--------------
Core orchestrator: ties together feature engineering, hard-decline rules,
weighted score calculation, fraud detection, reason code generation,
and audit persistence.

Entry point: score_application(input_data: dict) → dict
"""

from typing import List, Tuple, Dict

from .models import (
    LoanApplicationInput,
    ComputedFeatures,
    HardDeclineResult,
    RiskScoreOutput,
    EligibilityResult,
    RiskBand,
    Decision,
    CollateralType,
)
from .feature_engineering import engineer_features
from .rules_engine import evaluate_hard_rules, evaluate_soft_rules
from .config import (
    SCORE_WEIGHTS,
    RISK_BAND_LOW_MIN,
    RISK_BAND_MEDIUM_MIN,
    RISK_BAND_HIGH_MIN,
    FRAUD_GEO_MISMATCH_CODE,
    FRAUD_MULTIPLE_APPS_CODE,
    FRAUD_HIGH_ENQUIRY_CODE,
    FRAUD_VPN_PROXY_CODE,
    FRAUD_IP_COUNTRY_CODE,
    FRAUD_IP_STATE_CODE,
    HIGH_ENQUIRY_THRESHOLD,
    SECURED_LOAN_SCORE_BOOST,
    NONE_FLAG,
)
from .utils import (
    generate_application_id,
    utc_now_iso,
    to_serialisable,
    generate_explanation,
    logger,
    clamp,
)


# In-memory audit log (last 50 scores — no external DB needed)
_audit_log: list = []


# ──────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────

def score_application(input_data: dict) -> dict:
    """
    End-to-end risk scoring pipeline.

    Pipeline:
    1.  Validate & parse input (Pydantic)
    2.  Engineer features (EMI, FOIR, normalised scores for all 10 features)
    2.5 Loan eligibility engine (max income + collateral eligible amount)
    3.  Evaluate hard-decline rules (policy override)
    4.  Compute weighted risk score (10 features)
    4.5 Apply secured-loan score boost (if collateral present)
    5.  Determine risk band + decision (incorporating eligibility)
    6.  Build fraud flags
    7.  Generate reason codes
    8.  Build natural language explanation
    9.  Persist to MongoDB (audit trail)
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

    # ── 1. Parse & Validate ─────────────────────────────────────────
    app = LoanApplicationInput(**input_data)

    # ── 2. Feature Engineering (includes eligibility engine) ────────
    features = engineer_features(app)

    # ── 2.5 Compute model score baseline (always, even for hard declines) ──
    raw_score, factor_scores = _compute_weighted_score(features)

    if app.collateral and app.collateral.collateral_type != CollateralType.NONE:
        raw_score = raw_score * SECURED_LOAN_SCORE_BOOST
        logger.info("Secured loan boost applied (×%.2f)", SECURED_LOAN_SCORE_BOOST)

    risk_score = int(round(clamp(raw_score, 0.0, 1000.0)))
    risk_band_only = _band_from_score(risk_score)
    top_factors = _top_factors(factor_scores)

    # ── 3. Hard Decline Rules ────────────────────────────────────────
    decline_result = evaluate_hard_rules(app, features)

    if decline_result.is_declined:
        output = _build_decline_output(
            features=features,
            decline_result=decline_result,
            app=app,
            risk_score=risk_score,
            risk_band=risk_band_only,
            top_factors=top_factors,
        )
    else:
        # ── 5. Risk Band + Decision (with eligibility) ────────────────
        risk_band, decision = _classify(risk_score, features)

        # ── 6. Fraud Flags ────────────────────────────────────────────
        flags = _collect_fraud_flags(app)
        actual_flags = [f for f in flags if f != NONE_FLAG]

        # ── 6.5 Soft Rules & Thin File Check ──────────────────────────
        soft_reasons, new_fraud_flags = evaluate_soft_rules(app, features)
        flags.extend(new_fraud_flags)
        actual_flags.extend(new_fraud_flags)

        if app.bureau.cibil_score == 0 and app.bureau.credit_history_months == 0:
            flags.append("NO_BUREAU_HISTORY")
            actual_flags.append("NO_BUREAU_HISTORY")
            soft_reasons.append("NO_BUREAU_HISTORY")

        if actual_flags and NONE_FLAG in flags:
            flags.remove(NONE_FLAG)

        # Override decision to REVIEW if active fraud signals or soft rules
        if len(actual_flags) >= 2:
            decision = Decision.REVIEW
            logger.warning("Decision overridden to REVIEW due to multiple fraud flags: %s", flags)
            soft_reasons.append("MULTI_FRAUD_FLAG_REVIEW")
        elif actual_flags and decision == Decision.APPROVE:
            decision = Decision.REVIEW
            logger.warning("Decision overridden to REVIEW due to fraud flags: %s", flags)
            
        if soft_reasons and decision != Decision.DECLINE:
            decision = Decision.REVIEW

        # Downgrade to REDUCE for settled accounts if otherwise approved
        if app.bureau.has_settled_accounts and decision == Decision.APPROVE:
            decision = Decision.REDUCE
            logger.info("Decision downgraded to REDUCE due to past settled accounts")

        # ── 7. Reason Codes ───────────────────────────────────────────
        reason_codes = _generate_reason_codes(app, features)
        reason_codes.extend(soft_reasons)
        # ── 8. Explanation ────────────────────────────────────────────
        explanation = generate_explanation(
            decision=decision.value,
            risk_band=risk_band.value,
            reason_codes=reason_codes,
            flags=flags,
        )

        # Build eligibility result for output
        eligibility = EligibilityResult(
            max_income_eligible=features.max_income_eligible,
            max_collateral_eligible=features.max_collateral_eligible,
            final_max_eligible=features.final_max_eligible,
            is_counter_offer=features.is_counter_offer,
            counter_offer_amount=features.counter_offer_amount,
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
            eligibility=eligibility,
        )

    # ── 9. Persistence (Save to MongoDB if available) ───────────────────────
    audit_record = {
        "application_id": app_id,
        "timestamp":      ts,
        "input":          to_serialisable(app),
        "features":       to_serialisable(features),
        "output":         to_serialisable(output),
    }
    
    # Try saving to DB (from database.py)
    from .database import save_audit_record
    save_audit_record(audit_record)

    # Maintain in-memory log for backward compatibility
    _audit_log.append(audit_record)
    if len(_audit_log) > 50:
        _audit_log.pop(0)

    logger.info(
        "Result → score=%s band=%s decision=%s eligible=₹%.0f",
        output.risk_score, output.risk_band, output.decision,
        output.eligibility.final_max_eligible,
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
    Apply weight vector to normalised feature scores (all 10 features).

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
        "age":                 features.normalized_age,
        "location":            features.normalized_location,
        "collateral":          features.normalized_collateral,
    }

    weighted: Dict[str, float] = {}
    total = 0.0
    for factor, raw_score in factor_map.items():
        contribution = raw_score * SCORE_WEIGHTS[factor]
        weighted[factor] = round(contribution, 2)
        total += contribution

    return clamp(total, 0.0, 1000.0), weighted


def _band_from_score(score: int) -> RiskBand:
    """Map numeric score to risk band without decision logic."""
    if score >= RISK_BAND_LOW_MIN:
        return RiskBand.LOW
    if score >= RISK_BAND_MEDIUM_MIN:
        return RiskBand.MEDIUM
    if score >= RISK_BAND_HIGH_MIN:
        return RiskBand.HIGH
    return RiskBand.VERY_HIGH


def _classify(score: int, features: ComputedFeatures) -> Tuple[RiskBand, Decision]:
    """
    Map numeric risk score to band and decision, incorporating eligibility.

    If a counter-offer is needed, REDUCE is returned regardless of score band
    (we cannot approve the full requested amount).
    If eligible amount is < 50% of requested, force DECLINE.
    """
    requested = features.max_income_eligible  # used as reference baseline

    # If eligibility engine says we can't even offer 50% → decline
    # We reference final_max_eligible vs max income eligible as a proxy
    # (actual requested amount is not in features, so we use income headroom)
    if features.final_max_eligible <= 0:
        return RiskBand.VERY_HIGH, Decision.DECLINE

    # Counter-offer situation: eligible < requested
    if features.is_counter_offer and features.counter_offer_amount is None:
        # Below minimum viable loan → decline
        return RiskBand.VERY_HIGH, Decision.DECLINE

    # Standard band classification
    if score >= RISK_BAND_LOW_MIN:
        band = RiskBand.LOW
        decision = Decision.REDUCE if features.is_counter_offer else Decision.APPROVE
    elif score >= RISK_BAND_MEDIUM_MIN:
        band = RiskBand.MEDIUM
        decision = Decision.REDUCE
    elif score >= RISK_BAND_HIGH_MIN:
        band = RiskBand.HIGH
        decision = Decision.REVIEW
    else:
        band = RiskBand.VERY_HIGH
        decision = Decision.DECLINE

    return band, decision


def _collect_fraud_flags(app: LoanApplicationInput) -> List[str]:
    """Evaluate all fraud signals and return active flag codes."""
    flags: List[str] = []

    # Legacy geo mismatch flag (from FraudSignals)
    if app.fraud_signals.geo_mismatch:
        flags.append(FRAUD_GEO_MISMATCH_CODE)

    if app.fraud_signals.multiple_applications:
        flags.append(FRAUD_MULTIPLE_APPS_CODE)

    if app.bureau.enquiry_last_6_months > HIGH_ENQUIRY_THRESHOLD:
        flags.append(FRAUD_HIGH_ENQUIRY_CODE)

    # New IP / location fraud flags
    if app.location_signals.vpn_or_proxy_detected:
        flags.append(FRAUD_VPN_PROXY_CODE)
    elif app.location_signals.ip_country.upper() != app.location_signals.kyc_country.upper():
        flags.append(FRAUD_IP_COUNTRY_CODE)
    elif app.location_signals.ip_state.lower() != app.location_signals.kyc_state.lower():
        flags.append(FRAUD_IP_STATE_CODE)

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

    # ── CIBIL ──────────────────────────────────────────────────────
    if app.bureau.cibil_score >= 750:
        codes.append("GOOD_CIBIL")
    elif app.bureau.cibil_score >= 700:
        codes.append("AVERAGE_CIBIL")
    else:
        codes.append("WEAK_CIBIL")

    # ── FOIR ───────────────────────────────────────────────────────
    if features.foir_label == "GOOD":
        codes.append("LOW_FOIR")
    elif features.foir_label == "RISKY":
        codes.append("MODERATE_FOIR")
    else:
        codes.append("HIGH_FOIR")

    # ── DPD ────────────────────────────────────────────────────────
    if app.bureau.dpd_90_plus_count == 0:
        codes.append("NO_DPD")
    else:
        codes.append("DPD_PRESENT")

    # ── Credit Utilization ─────────────────────────────────────────
    if app.bureau.credit_utilization < 30:
        codes.append("LOW_CREDIT_UTILIZATION")
    elif app.bureau.credit_utilization >= 70:
        codes.append("HIGH_CREDIT_UTILIZATION")

    # ── Employment Tenure ──────────────────────────────────────────
    tenure = app.customer_profile.employment_tenure_months
    if tenure >= 24:
        codes.append("STABLE_EMPLOYMENT")
    elif tenure >= 12:
        codes.append("MODERATE_EMPLOYMENT")
    else:
        codes.append("SHORT_EMPLOYMENT")

    # ── Income Verification ────────────────────────────────────────
    if app.verification.income_match_percent >= 90:
        codes.append("INCOME_VERIFIED")
    else:
        codes.append("INCOME_MISMATCH")

    # ── Enquiries ──────────────────────────────────────────────────
    if app.bureau.enquiry_last_6_months <= 2:
        codes.append("LOW_ENQUIRIES")
    elif app.bureau.enquiry_last_6_months > HIGH_ENQUIRY_THRESHOLD:
        codes.append("HIGH_ENQUIRIES")

    # ── Credit History ─────────────────────────────────────────────
    if app.bureau.credit_history_months >= 36:
        codes.append("LONG_CREDIT_HISTORY")

    # ── Bureau Flags ───────────────────────────────────────────────
    if app.bureau.has_settled_accounts:
        codes.append("SETTLED_ACCOUNTS")
        codes.append("SETTLED_ACCOUNT_DISCOUNT")

    if app.bureau.has_npa:
        codes.append("NPA_PRESENT")

    # ── Age Band ───────────────────────────────────────────────────
    age = app.customer_profile.age
    if 29 <= age <= 45:
        codes.append("PRIME_AGE")
    elif age <= 25:
        codes.append("YOUNG_APPLICANT")
    elif age >= 55:
        codes.append("SENIOR_APPLICANT")

    # ── IP Location ────────────────────────────────────────────────
    ls = app.location_signals
    if (not ls.vpn_or_proxy_detected
            and ls.ip_country.upper() == ls.kyc_country.upper()
            and ls.ip_state.lower() == ls.kyc_state.lower()):
        codes.append("IP_LOCATION_MATCH")
    elif ls.ip_state.lower() != ls.kyc_state.lower():
        codes.append("IP_LOCATION_MISMATCH")

    # ── Collateral ─────────────────────────────────────────────────
    if app.collateral and app.collateral.collateral_type != CollateralType.NONE:
        codes.append("SECURED_LOAN")
        if features.ltv_ratio is not None:
            if features.ltv_ratio <= 0.60:
                codes.append("COLLATERAL_LOW_LTV")
            elif features.ltv_ratio > 0.75:
                codes.append("COLLATERAL_HIGH_LTV")
    else:
        codes.append("UNSECURED_LOAN")

    # ── Eligibility / Counter-offer ────────────────────────────────
    if features.is_counter_offer and features.counter_offer_amount is not None:
        codes.append("COUNTER_OFFER_GENERATED")

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
    risk_score: int,
    risk_band: RiskBand,
    top_factors: List[str],
) -> RiskScoreOutput:
    """Build a RiskScoreOutput for hard-declined applications."""
    explanation = generate_explanation(
        decision="DECLINE",
        risk_band=risk_band.value,
        reason_codes=decline_result.triggered_rules,
        flags=[],
    )

    # Still surface eligibility info even on decline
    eligibility = EligibilityResult(
        max_income_eligible=features.max_income_eligible,
        max_collateral_eligible=features.max_collateral_eligible,
        final_max_eligible=features.final_max_eligible,
        is_counter_offer=False,
        counter_offer_amount=None,
    )

    return RiskScoreOutput(
        risk_score=risk_score,
        risk_band=risk_band.value,
        decision=Decision.DECLINE.value,
        foir=round(features.foir, 4),
        flags=[NONE_FLAG],
        reason_codes=decline_result.triggered_rules,
        top_factors=top_factors,
        llm_explanation=explanation,
        eligibility=eligibility,
    )
