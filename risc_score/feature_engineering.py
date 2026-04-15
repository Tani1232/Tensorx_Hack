"""
feature_engineering.py
----------------------
Computes derived financial features (FOIR, proposed EMI) and normalises
each raw parameter to a 0–1000 score for the weighted scoring model.
"""

from models import (
    LoanApplicationInput,
    ComputedFeatures,
)
from config import (
    FOIR_GOOD_THRESHOLD,
    FOIR_RISKY_THRESHOLD,
    CIBIL_MIN,
    CIBIL_MAX,
    DPD_90_MAX_REFERENCE,
    ENQUIRY_MAX_REFERENCE,
    TENURE_MAX_REFERENCE,
)
from utils import calculate_emi, linear_scale, clamp, logger


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

    Returns a fully populated ComputedFeatures object.
    """
    # ── Step 1 : EMI Calculation ─────────────────────
    proposed_emi = calculate_emi(
        principal=app.loan_request.amount,
        tenure_months=app.loan_request.tenure_months,
    )
    logger.debug("Proposed EMI: ₹%.2f", proposed_emi)

    # ── Step 2 : FOIR ────────────────────────────────
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

    # ── Step 3 : Normalisation ───────────────────────
    norm_cibil = _normalise_cibil(app.bureau.cibil_score)
    norm_foir  = _normalise_foir(foir)
    norm_dpd   = _normalise_dpd(app.bureau.dpd_90_plus_count)
    norm_util  = _normalise_utilisation(app.bureau.credit_utilization)
    norm_enq   = _normalise_enquiries(app.bureau.enquiry_last_6_months)
    norm_ten   = _normalise_tenure(app.customer_profile.employment_tenure_months)
    norm_inc   = _normalise_income_verification(app.verification.income_match_percent)

    logger.debug(
        "Normalised scores → CIBIL:%.0f FOIR:%.0f DPD:%.0f UTIL:%.0f "
        "ENQ:%.0f TENURE:%.0f INC:%.0f",
        norm_cibil, norm_foir, norm_dpd, norm_util, norm_enq, norm_ten, norm_inc,
    )

    return ComputedFeatures(
        proposed_emi=proposed_emi,
        foir=foir,
        foir_label=foir_label,
        normalized_cibil=norm_cibil,
        normalized_foir=norm_foir,
        normalized_dpd=norm_dpd,
        normalized_utilization=norm_util,
        normalized_enquiry=norm_enq,
        normalized_tenure=norm_ten,
        normalized_income_verification=norm_inc,
    )


# ──────────────────────────────────────────────
# Private Normalisation Functions
# ──────────────────────────────────────────────

def _normalise_cibil(score: int) -> float:
    """
    Map CIBIL [300, 900] linearly to [0, 1000].
    Higher CIBIL → higher normalised score.
    """
    return linear_scale(score, low=CIBIL_MIN, high=CIBIL_MAX, invert=False)


def _normalise_foir(foir: float) -> float:
    """
    Map FOIR [0, 0.65+] to [0, 1000] — inverted (lower FOIR → higher score).
    Capped at 0.65 (hard-decline threshold acts as ceiling).
    """
    # Invert: foir=0 → 1000, foir=0.65 → 0
    return linear_scale(foir, low=0.0, high=0.65, invert=True)


def _normalise_dpd(dpd_count: int) -> float:
    """
    Map DPD 90+ count [0, MAX_REF] to [0, 1000] — inverted.
    0 DPD → 1000, MAX_REF+ → 0.
    """
    return linear_scale(dpd_count, low=0, high=DPD_90_MAX_REFERENCE, invert=True)


def _normalise_utilisation(utilization_pct: float) -> float:
    """
    Map credit utilization [0%, 100%] to [0, 1000] — inverted.
    0% utilization → 1000, 100% → 0.
    """
    return linear_scale(utilization_pct, low=0.0, high=100.0, invert=True)


def _normalise_enquiries(count: int) -> float:
    """
    Map enquiry count [0, MAX_REF] to [0, 1000] — inverted.
    0 enquiries → 1000, MAX_REF+ → 0.
    """
    return linear_scale(count, low=0, high=ENQUIRY_MAX_REFERENCE, invert=True)


def _normalise_tenure(months: int) -> float:
    """
    Map employment tenure [0, MAX_REF months] to [0, 1000].
    Longer tenure → higher score.
    """
    return linear_scale(months, low=0, high=TENURE_MAX_REFERENCE, invert=False)


def _normalise_income_verification(match_pct: float) -> float:
    """
    Map income verification [0%, 100%] to [0, 1000].
    Higher match → higher score.
    """
    return linear_scale(match_pct, low=0.0, high=100.0, invert=False)
