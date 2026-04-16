"""
feature_engineering.py
----------------------
Computes derived financial features (FOIR, proposed EMI) and normalises
each raw parameter to a 0–1000 score for the weighted scoring model.

Also calls the eligibility engine to determine max loan amount and
counter-offer flag.
"""

import math
from typing import Optional, Tuple

from models import (
    LoanApplicationInput,
    ComputedFeatures,
    CollateralData,
    CollateralType,
    LocationSignals,
)
from config import (
    FOIR_GOOD_THRESHOLD,
    FOIR_RISKY_THRESHOLD,
    CIBIL_MIN,
    CIBIL_MAX,
    DPD_90_MAX_REFERENCE,
    ENQUIRY_MAX_REFERENCE,
    TENURE_MAX_REFERENCE,
    AGE_BAND_SCORES,
    COLLATERAL_LTV_MAP,
)
from utils import calculate_emi, linear_scale, clamp, logger
from eligibility_engine import compute_eligibility


# ──────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────

def engineer_features(app: LoanApplicationInput) -> ComputedFeatures:
    """
    Derive all intermediate features needed for scoring.

    Steps:
    1. Compute proposed EMI from loan request parameters.
    2. Compute FOIR and classify into a policy band.
    3. Normalise each raw feature to a 0–1000 score.
    4. Normalise new features: age, IP location, collateral LTV.
    5. Run eligibility engine to get max eligible amount + counter-offer.

    Returns a fully populated ComputedFeatures object.
    """
    # ── Step 1 : EMI Calculation ─────────────────────────────────────────────
    proposed_emi = calculate_emi(
        principal=app.loan_request.amount,
        tenure_months=app.loan_request.tenure_months,
    )
    logger.debug("Proposed EMI: ₹%.2f", proposed_emi)

    # ── Step 2 : FOIR ────────────────────────────────────────────────────────
    total_obligations = app.liabilities.existing_emis + proposed_emi
    foir = total_obligations / app.customer_profile.monthly_income
    foir = round(foir, 4)

    if foir <= FOIR_GOOD_THRESHOLD:
        foir_label = "GOOD"
    elif foir <= FOIR_RISKY_THRESHOLD:
        foir_label = "RISKY"
    else:
        foir_label = "DECLINE"

    logger.debug("FOIR: %.4f (%s)", foir, foir_label)

    # ── Step 3 : Core Normalisation ──────────────────────────────────────────
    norm_cibil = _normalise_cibil(app.bureau.cibil_score)
    norm_foir  = _normalise_foir(foir)
    norm_dpd   = _normalise_dpd(app.bureau.dpd_90_plus_count)
    norm_util  = _normalise_utilisation(app.bureau.credit_utilization)
    norm_enq   = _normalise_enquiries(app.bureau.enquiry_last_6_months)
    norm_ten   = _normalise_tenure(app.customer_profile.employment_tenure_months)
    norm_inc   = _normalise_income_verification(app.verification.income_match_percent)

    # ── Step 4 : New Feature Normalisation ───────────────────────────────────
    norm_age      = _normalise_age(app.customer_profile.age)
    norm_location = _normalise_location(app.location_signals)
    norm_collateral, ltv_ratio = _normalise_collateral(
        app.collateral, app.loan_request.amount
    )

    logger.debug(
        "Normalised scores → CIBIL:%.0f FOIR:%.0f DPD:%.0f UTIL:%.0f "
        "ENQ:%.0f TENURE:%.0f INC:%.0f AGE:%.0f LOC:%.0f COLL:%.0f",
        norm_cibil, norm_foir, norm_dpd, norm_util, norm_enq,
        norm_ten, norm_inc, norm_age, norm_location, norm_collateral,
    )

    # ── Step 5 : Eligibility Engine ──────────────────────────────────────────
    eligibility = compute_eligibility(app, proposed_emi)

    return ComputedFeatures(
        proposed_emi=proposed_emi,
        foir=foir,
        foir_label=foir_label,
        # Core
        normalized_cibil=norm_cibil,
        normalized_foir=norm_foir,
        normalized_dpd=norm_dpd,
        normalized_utilization=norm_util,
        normalized_enquiry=norm_enq,
        normalized_tenure=norm_ten,
        normalized_income_verification=norm_inc,
        # New
        normalized_age=norm_age,
        normalized_location=norm_location,
        normalized_collateral=norm_collateral,
        # Eligibility
        ltv_ratio=eligibility["ltv_ratio"],
        max_income_eligible=eligibility["max_income_eligible"],
        max_collateral_eligible=eligibility["max_collateral_eligible"],
        final_max_eligible=eligibility["final_max_eligible"],
        is_counter_offer=eligibility["is_counter_offer"],
        counter_offer_amount=eligibility["counter_offer_amount"],
    )


# ──────────────────────────────────────────────
# Private Normalisation — Core Features
# ──────────────────────────────────────────────

def _normalise_cibil(score: int) -> float:
    """Map CIBIL [300, 900] linearly to [0, 1000]. Higher = better."""
    if score == 0:
        return 500.0
    return linear_scale(score, low=CIBIL_MIN, high=CIBIL_MAX, invert=False)


def _normalise_foir(foir: float) -> float:
    """
    Two-segment piecewise function:
    FOIR 0–50%: map to 1000 → 600
    FOIR 50–65%: map to 600 → 0
    FOIR > 65%: capped at 0
    """
    if foir <= 0.50:
        score = 600.0 + ((0.50 - foir) / 0.50) * 400.0
    elif foir <= 0.65:
        score = ((0.65 - foir) / 0.15) * 600.0
    else:
        score = 0.0
    return clamp(score, 0.0, 1000.0)


def _normalise_dpd(dpd_count: int) -> float:
    """Map DPD 90+ count [0, MAX_REF] to [0, 1000] — inverted. 0 DPD → 1000."""
    return linear_scale(dpd_count, low=0, high=DPD_90_MAX_REFERENCE, invert=True)


def _normalise_utilisation(utilization_pct: float) -> float:
    """Map credit utilization [0%, 100%] to [0, 1000] — inverted. 0% → 1000."""
    return linear_scale(utilization_pct, low=0.0, high=100.0, invert=True)


def _normalise_enquiries(count: int) -> float:
    """Map enquiry count [0, MAX_REF] to [0, 1000] — inverted. 0 → 1000."""
    return linear_scale(count, low=0, high=ENQUIRY_MAX_REFERENCE, invert=True)


def _normalise_tenure(months: int) -> float:
    """Map employment tenure [0, MAX_REF months] to [0, 1000]. Longer = better."""
    return linear_scale(months, low=0, high=TENURE_MAX_REFERENCE, invert=False)


def _normalise_income_verification(match_pct: float) -> float:
    """Map income verification [0%, 100%] to [0, 1000]. Higher match = better."""
    return linear_scale(match_pct, low=0.0, high=100.0, invert=False)


# ──────────────────────────────────────────────
# Private Normalisation — New Features
# ──────────────────────────────────────────────

def _normalise_age(age: int) -> float:
    """
    Map applicant age to a 0–1000 score using predefined age bands.
    Ages outside all bands (< 18 or > 70) are gated out before reaching
    this function, but we return 0 as a safety fallback.
    """
    for min_age, max_age, score in AGE_BAND_SCORES:
        if min_age <= age <= max_age:
            return float(score)
    return 0.0   # Safety fallback — should be caught by hard gate


def _normalise_location(signals: LocationSignals) -> float:
    """
    Score IP location vs KYC address consistency.

    1000 → State match + no VPN  (fully trusted)
     500 → State mismatch but country matches (travel / relocation)
       0 → Country mismatch OR VPN/Proxy detected (fraud risk)

    VPN/Proxy check is redundant here (hard gate fires first) but kept
    as a defensive fallback so the score accurately reflects the signal.
    """
    if signals.vpn_or_proxy_detected:
        return 0.0

    if signals.ip_country.upper() != signals.kyc_country.upper():
        return 0.0   # International IP — very high fraud risk

    if signals.ip_state.lower() == signals.kyc_state.lower():
        return 1000.0   # Perfect state-level match

    # Same country, different state — partial match (travelling, WFH, etc.)
    return 500.0


def _normalise_collateral(
    collateral: Optional[CollateralData],
    loan_amount: float,
) -> Tuple[float, Optional[float]]:
    """
    Score collateral quality based on LTV ratio.

    Returns:
        (normalised_score_0_to_1000, ltv_ratio or None for unsecured)

    Scoring bands (lower LTV = more collateral cushion = better score):
        LTV ≤ 0.60 → 1000  (very safe)
        LTV ≤ 0.75 → 700
        LTV ≤ 0.85 → 400
        LTV  > 0.85 → 100  (very thin margin — LTV gate may also fire)
        No collateral → 0  (unsecured — not penalised, just no boost)
    """
    if collateral is None or collateral.collateral_type == CollateralType.NONE:
        return 0.0, None

    if collateral.market_value <= 0:
        return 0.0, None

    ltv = loan_amount / collateral.market_value

    if ltv <= 0.60:
        score = 1000.0
    elif ltv <= 0.75:
        score = 700.0
    elif ltv <= 0.85:
        score = 400.0
    else:
        score = 100.0

    return score, round(ltv, 4)
