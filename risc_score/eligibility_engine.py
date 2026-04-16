"""
eligibility_engine.py
---------------------
Loan Eligibility Engine — answers *how much* a borrower can receive.

Two parallel checks run independently and the stricter (lower) result wins:
  1. Income-based eligibility  : derived from available FOIR headroom
  2. Collateral-based cap      : LTV × collateral market value (secured loans only)

The engine also generates counter-offer amounts when the requested loan
exceeds the maximum eligible amount.

Public API:
    compute_eligibility(app, proposed_emi) → fills ComputedFeatures eligibility fields
"""

import math
from typing import Optional

from models import LoanApplicationInput, CollateralData, CollateralType
from config import (
    ANNUAL_INTEREST_RATE,
    MAX_FOIR_FOR_ELIGIBILITY,
    COLLATERAL_LTV_MAP,
    MIN_VIABLE_LOAN_AMOUNT,
)
from utils import logger


# ──────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────

def compute_eligibility(
    app: LoanApplicationInput,
    proposed_emi: float,
) -> dict:
    """
    Compute income-based and collateral-based loan eligibility.

    Args:
        app:          Full validated loan application.
        proposed_emi: EMI calculated for the requested loan (from feature_engineering).

    Returns:
        dict with keys:
            max_income_eligible      : float
            max_collateral_eligible  : float   (math.inf for unsecured loans)
            final_max_eligible       : float
            ltv_ratio                : Optional[float]
            is_counter_offer         : bool
            counter_offer_amount     : Optional[float]
    """
    requested = app.loan_request.amount
    tenure    = app.loan_request.tenure_months
    income    = app.customer_profile.monthly_income

    # ── 1. Income-Based Eligibility ─────────────────────────────────────────
    max_income_eligible = _income_based_max(
        income=income,
        existing_emis=app.liabilities.existing_emis,
        tenure_months=tenure,
    )
    logger.debug("Income-based max eligible: ₹%.0f", max_income_eligible)

    # ── 2. Collateral-Based Cap ─────────────────────────────────────────────
    ltv_ratio: Optional[float] = None
    if app.collateral and app.collateral.collateral_type != CollateralType.NONE:
        collateral_max, ltv_ratio = _collateral_based_max(
            collateral=app.collateral,
            loan_amount=requested,
        )
        logger.debug(
            "Collateral-based max: ₹%.0f  LTV: %.2f",
            collateral_max, ltv_ratio if ltv_ratio else 0.0,
        )
    else:
        collateral_max = math.inf   # Unsecured — no collateral ceiling
        logger.debug("Unsecured loan — no collateral cap applied.")

    # ── 3. Final Eligible Amount ─────────────────────────────────────────────
    final_max = min(max_income_eligible, collateral_max)
    final_max = max(final_max, 0.0)  # Clamp negatives to 0

    if app.bureau.has_settled_accounts and final_max > 0:
        final_max = final_max * 0.85

    # ── 4. Counter-Offer Logic ───────────────────────────────────────────────
    is_counter_offer = False
    counter_offer_amount: Optional[float] = None

    if final_max < requested:
        is_counter_offer = True
        if final_max >= MIN_VIABLE_LOAN_AMOUNT:
            counter_offer_amount = round(final_max, -3)   # Round to nearest ₹1000
            logger.info(
                "Counter-offer generated: ₹%.0f (requested ₹%.0f)",
                counter_offer_amount, requested,
            )
        else:
            logger.info(
                "Eligible amount ₹%.0f is below minimum viable ₹%.0f — no counter-offer.",
                final_max, MIN_VIABLE_LOAN_AMOUNT,
            )

    return {
        "max_income_eligible":     round(max_income_eligible, 2),
        "max_collateral_eligible": round(collateral_max, 2) if collateral_max != math.inf else -1.0,
        "final_max_eligible":      round(final_max, 2),
        "ltv_ratio":               round(ltv_ratio, 4) if ltv_ratio is not None else None,
        "is_counter_offer":        is_counter_offer,
        "counter_offer_amount":    counter_offer_amount,
    }


# ──────────────────────────────────────────────
# Private Helpers
# ──────────────────────────────────────────────

def _income_based_max(
    income: float,
    existing_emis: float,
    tenure_months: int,
) -> float:
    """
    Maximum loan affordable based on FOIR headroom.

    Steps:
      available_emi  = (MAX_FOIR × income) − existing_emis
      annuity_factor = P for EMI = 1, computed from rate & tenure
      max_loan       = available_emi × annuity_factor
    """
    max_total_emi      = MAX_FOIR_FOR_ELIGIBILITY * income
    available_emi_room = max_total_emi - existing_emis

    if available_emi_room <= 0:
        return 0.0

    monthly_rate = ANNUAL_INTEREST_RATE / 12

    if monthly_rate == 0 or tenure_months == 0:
        return available_emi_room * tenure_months

    # Standard annuity formula: P = EMI × [(1 - (1+r)^-n) / r]
    annuity_factor = (1 - (1 + monthly_rate) ** (-tenure_months)) / monthly_rate
    return available_emi_room * annuity_factor


def _collateral_based_max(
    collateral: CollateralData,
    loan_amount: float,
) -> tuple:
    """
    Maximum loan permitted by LTV policy.

    Returns:
        (max_collateral_amount, ltv_ratio_at_requested_amount)
    """
    ltv_limit = COLLATERAL_LTV_MAP.get(collateral.collateral_type.value, 0.0)
    max_collateral_amount = collateral.market_value * ltv_limit

    # LTV ratio at the currently requested loan amount (for scoring & reporting)
    ltv_ratio = loan_amount / collateral.market_value if collateral.market_value > 0 else 1.0

    return max_collateral_amount, ltv_ratio
