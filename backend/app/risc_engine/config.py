"""
config.py
---------
Central configuration registry for all thresholds, weights, and external settings.
Modify this file to tune the scoring engine without touching business logic.
"""

from dataclasses import dataclass, field
from typing import Dict, Tuple, List


# ──────────────────────────────────────────────
# MongoDB Configuration
# ──────────────────────────────────────────────

MONGO_URI: str = "mongodb://localhost:27017"
MONGO_DB: str = "risk_scoring_db"
MONGO_COLLECTION: str = "loan_applications"


# ──────────────────────────────────────────────
# Hard Decline Thresholds — Identity / Age
# ──────────────────────────────────────────────

HARD_DECLINE_AGE_MIN: int = 18          # Age < 18  → UNDERAGE
HARD_DECLINE_AGE_MAX: int = 70          # Age > 70  → AGE_ABOVE_POLICY_LIMIT


# ──────────────────────────────────────────────
# Hard Decline Thresholds — Credit & Income
# ──────────────────────────────────────────────

HARD_DECLINE_FOIR_THRESHOLD: float = 0.65          # FOIR > 65% → immediate decline
HARD_DECLINE_CIBIL_MIN: int = 650                   # CIBIL < 650 → decline
HARD_DECLINE_DPD_90_MAX: int = 3                    # DPD 90+ ≥ 3 → decline
HARD_DECLINE_INCOME_MATCH_MIN: float = 70.0         # Income match < 70% → decline


# ──────────────────────────────────────────────
# FOIR Bands
# ──────────────────────────────────────────────

FOIR_GOOD_THRESHOLD: float = 0.50                   # ≤ 50%  → GOOD
FOIR_RISKY_THRESHOLD: float = 0.65                  # 51–65% → RISKY
MAX_FOIR_FOR_ELIGIBILITY: float = 0.50              # Target FOIR cap for eligibility calc


# ──────────────────────────────────────────────
# Loan EMI Parameters
# ──────────────────────────────────────────────

ANNUAL_INTEREST_RATE: float = 0.14                  # 14% p.a. for EMI calculation
MIN_VIABLE_LOAN_AMOUNT: float = 10_000.0            # Counter-offer below this → full decline


# ──────────────────────────────────────────────
# Age Band → Normalised Score (0–1000)
# ──────────────────────────────────────────────
# List of (min_age, max_age, score) tuples, evaluated in order.

AGE_BAND_SCORES: List[Tuple[int, int, int]] = [
    (18, 22,  200),
    (23, 28,  550),
    (29, 45, 1000),
    (46, 55,  800),
    (56, 70,  600),
]
# Ages outside all bands (< 18 or > 70) are gated out before scoring.


# ──────────────────────────────────────────────
# Collateral LTV Limits  (Loan-to-Value ratios)
# ──────────────────────────────────────────────

COLLATERAL_LTV_MAP: Dict[str, float] = {
    "residential_property": 0.75,
    "commercial_property":  0.65,
    "gold":                 0.75,
    "fixed_deposit":        0.90,
    "stocks_mf":            0.50,
    "none":                 0.00,   # Unsecured — no collateral limit applies
}

# Score multiplier applied to the final weighted score when loan is secured.
SECURED_LOAN_SCORE_BOOST: float = 1.08   # 8% boost


# ──────────────────────────────────────────────
# Scoring Weights (must sum to 1.0)
# ──────────────────────────────────────────────

SCORE_WEIGHTS: Dict[str, float] = {
    "cibil":               0.23,
    "foir":                0.18,
    "dpd":                 0.14,
    "credit_utilization":  0.09,
    "enquiry":             0.09,
    "employment_tenure":   0.09,
    "income_verification": 0.09,
    "age":                 0.04,   # Age band scoring
    "location":            0.03,   # IP location match
    "collateral":          0.02,   # Collateral / LTV quality
}

assert abs(sum(SCORE_WEIGHTS.values()) - 1.0) < 1e-9, "Score weights must sum to 1.0"


# ──────────────────────────────────────────────
# Risk Band Thresholds
# ──────────────────────────────────────────────

RISK_BAND_LOW_MIN: int = 700        # 700–1000 → LOW  → APPROVE
RISK_BAND_MEDIUM_MIN: int = 550     # 550–699  → MEDIUM → REDUCE
RISK_BAND_HIGH_MIN: int = 400       # 400–549  → HIGH → REVIEW
                                    # < 400    → VERY_HIGH → DECLINE


# ──────────────────────────────────────────────
# Normalisation Reference Ranges
# (score of 1000 at min risk, 0 at max risk)
# ──────────────────────────────────────────────

# CIBIL: 300 (worst) → 900 (best)
CIBIL_MIN: int = 300
CIBIL_MAX: int = 900

# DPD 90+ : 0 (best) → 10+ (worst)
DPD_90_MAX_REFERENCE: int = 10

# Enquiries last 6M: 0 (best) → 8+ (worst)
ENQUIRY_MAX_REFERENCE: int = 8

# Employment tenure: 0 (worst) → 60+ months (best)
TENURE_MAX_REFERENCE: int = 60

# Credit utilization: 0% (best) → 100% (worst)
# Income verification: 100% (best) → 0% (worst)


# ──────────────────────────────────────────────
# Fraud Signal Codes
# ──────────────────────────────────────────────

FRAUD_GEO_MISMATCH_CODE: str      = "FRAUD_GEO_MISMATCH"
FRAUD_MULTIPLE_APPS_CODE: str     = "FRAUD_MULTIPLE_APPLICATIONS"
FRAUD_HIGH_ENQUIRY_CODE: str      = "FRAUD_HIGH_ENQUIRY_COUNT"
FRAUD_VPN_PROXY_CODE: str         = "FRAUD_VPN_PROXY_DETECTED"
FRAUD_IP_COUNTRY_CODE: str        = "FRAUD_IP_COUNTRY_MISMATCH"
FRAUD_IP_STATE_CODE: str          = "FRAUD_IP_STATE_MISMATCH"
FRAUD_AGE_MISMATCH_CODE: str      = "AGE_MISMATCH_DETECTED"
FRAUD_NO_BUREAU_CODE: str         = "NO_BUREAU_HISTORY"
HIGH_ENQUIRY_THRESHOLD: int       = 5     # > 5 enquiries in 6M → flag

NONE_FLAG: str = "NONE"


# ──────────────────────────────────────────────
# Reason Code Definitions
# ──────────────────────────────────────────────

REASON_CODES = {
    # ── Positive ───────────────────────────────
    "GOOD_CIBIL":              "CIBIL score is strong (≥ 750)",
    "AVERAGE_CIBIL":           "CIBIL score is acceptable (650–749)",
    "LOW_FOIR":                "FOIR is within healthy limits (≤ 50%)",
    "MODERATE_FOIR":           "FOIR is moderate (51–65%)",
    "NO_DPD":                  "No DPD 90+ delinquencies",
    "LOW_CREDIT_UTILIZATION":  "Credit utilization is low (< 30%)",
    "STABLE_EMPLOYMENT":       "Employment tenure is stable (≥ 24 months)",
    "MODERATE_EMPLOYMENT":     "Employment tenure is moderate (12–23 months)",
    "INCOME_VERIFIED":         "Income fully verified (≥ 90%)",
    "LOW_ENQUIRIES":           "Low credit enquiry count (≤ 2)",
    "LONG_CREDIT_HISTORY":     "Long credit history (≥ 36 months)",
    "PRIME_AGE":               "Applicant is in prime earning age bracket (29–45)",
    "IP_LOCATION_MATCH":       "IP location matches KYC address state",
    "SECURED_LOAN":            "Loan is secured by collateral — risk reduced",
    "COLLATERAL_LOW_LTV":      "Collateral LTV is within safe limits (≤ 60%)",

    # ── Negative ───────────────────────────────
    "WEAK_CIBIL":              "CIBIL score is weak (< 700)",
    "HIGH_FOIR":               "FOIR is elevated (> 50%)",
    "DPD_PRESENT":             "DPD 90+ delinquencies exist",
    "HIGH_CREDIT_UTILIZATION": "Credit utilization is high (≥ 70%)",
    "SHORT_EMPLOYMENT":        "Employment tenure is short (< 12 months)",
    "INCOME_MISMATCH":         "Income verification below threshold",
    "HIGH_ENQUIRIES":          "High credit enquiry count (> 5)",
    "SETTLED_ACCOUNTS":        "Settled accounts observed in bureau",
    "NPA_PRESENT":             "NPA / write-off found in bureau",
    "YOUNG_APPLICANT":         "Applicant age is young (18–25); limited credit history expected",
    "SENIOR_APPLICANT":        "Applicant is senior (55+); income sustainability considered",
    "IP_LOCATION_MISMATCH":    "IP location does not match KYC address state",
    "UNSECURED_LOAN":          "Loan is unsecured — credit profile is primary risk signal",
    "COLLATERAL_HIGH_LTV":     "Collateral LTV is elevated (> 75%)",
    "COUNTER_OFFER_GENERATED": "Eligible amount is less than requested — counter-offer made",
    "MULTI_FRAUD_FLAG_REVIEW": "Multiple fraud flags detected — mandatory review",
    "YOUNG_THIN_FILE_REVIEW":  "Young applicant with thin credit file — mandatory review",
    "NO_BUREAU_HISTORY":       "No prior credit history exists — mandatory review",
    "SETTLED_ACCOUNT_DISCOUNT":"Eligible amount reduced by 15% due to past settled accounts",
    "AGE_MISMATCH_DETECTED":   "Age mismatch detected during Video KYC — mandatory review",
}
