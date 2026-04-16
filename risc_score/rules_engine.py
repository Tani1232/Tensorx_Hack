"""
rules_engine.py
---------------
Hard-decline policy engine.
Evaluates binary rules that override the probabilistic risk score.
Any triggered rule results in an immediate DECLINE decision.
"""

from typing import List

from models import LoanApplicationInput, HardDeclineResult, ComputedFeatures, CollateralType
from config import (
    HARD_DECLINE_FOIR_THRESHOLD,
    HARD_DECLINE_CIBIL_MIN,
    HARD_DECLINE_DPD_90_MAX,
    HARD_DECLINE_INCOME_MATCH_MIN,
    HARD_DECLINE_AGE_MIN,
    HARD_DECLINE_AGE_MAX,
    COLLATERAL_LTV_MAP,
)
from utils import logger


# ──────────────────────────────────────────────
# Rule Registry
# ──────────────────────────────────────────────
# Each rule is a function: (app, features) → (triggered: bool, code: str)
# Keeping rules as callables makes them easy to add/remove/order.

# ── Identity / Age Rules ───────────────────────────────────────────────────

def _rule_age_below_minimum(
    app: LoanApplicationInput, features: ComputedFeatures
) -> tuple[bool, str]:
    """Age < 18 → DECLINE. Lending to minors is illegal."""
    triggered = app.customer_profile.age < HARD_DECLINE_AGE_MIN
    return triggered, "UNDERAGE"


def _rule_age_above_maximum(
    app: LoanApplicationInput, features: ComputedFeatures
) -> tuple[bool, str]:
    """Age > 70 → DECLINE. Exceeds policy age limit."""
    triggered = app.customer_profile.age > HARD_DECLINE_AGE_MAX
    return triggered, "AGE_ABOVE_POLICY_LIMIT"


# ── Fraud / Location Rules ─────────────────────────────────────────────────

def _rule_vpn_proxy_detected(
    app: LoanApplicationInput, features: ComputedFeatures
) -> tuple[bool, str]:
    """VPN or Proxy detected → DECLINE. Masking origin is a strong fraud signal."""
    triggered = app.location_signals.vpn_or_proxy_detected
    return triggered, "VPN_PROXY_DECLINED"


# ── Credit Rules ───────────────────────────────────────────────────────────

def _rule_foir_exceeded(
    app: LoanApplicationInput, features: ComputedFeatures
) -> tuple[bool, str]:
    """FOIR > 65% → DECLINE."""
    triggered = features.foir > HARD_DECLINE_FOIR_THRESHOLD
    return triggered, "FOIR_DECLINE"


def _rule_npa_present(
    app: LoanApplicationInput, features: ComputedFeatures
) -> tuple[bool, str]:
    """NPA or write-off on bureau → DECLINE."""
    triggered = app.bureau.has_npa
    return triggered, "NPA_WRITEOFF"


def _rule_cibil_below_minimum(
    app: LoanApplicationInput, features: ComputedFeatures
) -> tuple[bool, str]:
    """CIBIL < 650 → DECLINE."""
    if app.bureau.cibil_score == 0 and app.bureau.credit_history_months == 0:
        return False, "CIBIL_BELOW_MINIMUM"
    triggered = app.bureau.cibil_score < HARD_DECLINE_CIBIL_MIN
    return triggered, "CIBIL_BELOW_MINIMUM"


def _rule_dpd_excessive(
    app: LoanApplicationInput, features: ComputedFeatures
) -> tuple[bool, str]:
    """DPD 90+ count ≥ 3 → DECLINE."""
    triggered = app.bureau.dpd_90_plus_count >= HARD_DECLINE_DPD_90_MAX
    return triggered, "DPD_EXCESSIVE"


def _rule_income_verification_low(
    app: LoanApplicationInput, features: ComputedFeatures
) -> tuple[bool, str]:
    """Income match < 70% → DECLINE."""
    triggered = app.verification.income_match_percent < HARD_DECLINE_INCOME_MATCH_MIN
    return triggered, "INCOME_VERIFICATION_LOW"


# ── Collateral / LTV Rule ──────────────────────────────────────────────────

def _rule_ltv_exceeded(
    app: LoanApplicationInput, features: ComputedFeatures
) -> tuple[bool, str]:
    """
    LTV ratio exceeds the policy limit for the given collateral type → DECLINE.
    Unsecured loans (no collateral) always pass this rule.
    """
    if app.collateral is None or app.collateral.collateral_type == CollateralType.NONE:
        return False, "LTV_EXCEEDED"   # Not applicable for unsecured loans

    ltv_limit = COLLATERAL_LTV_MAP.get(app.collateral.collateral_type.value, 0.0)
    if ltv_limit == 0.0:
        return False, "LTV_EXCEEDED"

    if app.collateral.market_value <= 0:
        return True, "LTV_EXCEEDED"   # Invalid collateral value

    actual_ltv = app.loan_request.amount / app.collateral.market_value
    triggered = actual_ltv > ltv_limit
    return triggered, "LTV_EXCEEDED"


# ── Ordered rule list (evaluated top-down, all rules always run) ───────────
_ALL_RULES = [
    # Identity gates first (fastest, most absolute)
    _rule_age_below_minimum,
    _rule_age_above_maximum,
    _rule_vpn_proxy_detected,
    # Credit rules
    _rule_foir_exceeded,
    _rule_npa_present,
    _rule_cibil_below_minimum,
    _rule_dpd_excessive,
    _rule_income_verification_low,
    # Collateral rule
    _rule_ltv_exceeded,
]


# ──────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────

def evaluate_hard_rules(
    app: LoanApplicationInput,
    features: ComputedFeatures,
) -> HardDeclineResult:
    """
    Run all hard-decline rules against the application.

    Returns a HardDeclineResult containing:
    - is_declined: True if any rule triggered.
    - triggered_rules: List of rule codes that fired.

    All rules are always evaluated (not short-circuited) so that the full
    set of decline reasons can be surfaced to the applicant.
    """
    triggered_rules: List[str] = []

    for rule_fn in _ALL_RULES:
        triggered, code = rule_fn(app, features)
        if triggered:
            logger.warning("Hard decline rule triggered: %s", code)
            triggered_rules.append(code)

    result = HardDeclineResult(
        is_declined=bool(triggered_rules),
        triggered_rules=triggered_rules,
    )

    if result.is_declined:
        logger.info(
            "Application DECLINED by policy engine. Rules: %s",
            triggered_rules,
        )
    else:
        logger.info("Application passed all hard-decline rules.")

    return result

def evaluate_soft_rules(
    app: LoanApplicationInput, features: ComputedFeatures
) -> tuple[List[str], List[str]]:
    """
    Evaluate soft rules that override decision to REVIEW.
    Returns: (review_reasons, new_fraud_flags)
    """
    review_reasons = []
    fraud_flags = []
    
    if app.customer_profile.age <= 23 and app.bureau.credit_history_months < 12:
        review_reasons.append("YOUNG_THIN_FILE_REVIEW")
        
    if app.verification.age_mismatch_flag:
        fraud_flags.append("AGE_MISMATCH_DETECTED")
        review_reasons.append("AGE_MISMATCH_DETECTED")
        
    return review_reasons, fraud_flags
