"""
rules_engine.py
---------------
Hard-decline policy engine.
Evaluates binary rules that override the probabilistic risk score.
Any triggered rule results in an immediate DECLINE decision.
"""

from typing import List

from models import LoanApplicationInput, HardDeclineResult, ComputedFeatures
from config import (
    HARD_DECLINE_FOIR_THRESHOLD,
    HARD_DECLINE_CIBIL_MIN,
    HARD_DECLINE_DPD_90_MAX,
    HARD_DECLINE_INCOME_MATCH_MIN,
)
from utils import logger


# ──────────────────────────────────────────────
# Rule Registry
# ──────────────────────────────────────────────
# Each rule is a function: (app, features) → (triggered: bool, code: str)
# Keeping rules as callables makes them easy to add/remove/order.

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


# Ordered list of all rules (evaluated top-down)
_ALL_RULES = [
    _rule_foir_exceeded,
    _rule_npa_present,
    _rule_cibil_below_minimum,
    _rule_dpd_excessive,
    _rule_income_verification_low,
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
