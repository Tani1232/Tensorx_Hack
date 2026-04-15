"""
config.py
---------
Central configuration registry for all thresholds, weights, and external settings.
Modify this file to tune the scoring engine without touching business logic.
"""

from dataclasses import dataclass, field
from typing import Dict


# ──────────────────────────────────────────────
# MongoDB Configuration
# ──────────────────────────────────────────────

MONGO_URI: str = "mongodb://localhost:27017"
MONGO_DB: str = "risk_scoring_db"
MONGO_COLLECTION: str = "loan_applications"


# ──────────────────────────────────────────────
# Hard Decline Thresholds
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


# ──────────────────────────────────────────────
# Loan EMI Parameters
# ──────────────────────────────────────────────

ANNUAL_INTEREST_RATE: float = 0.14                  # 14% p.a. flat rate for EMI calculation


# ──────────────────────────────────────────────
# Scoring Weights (must sum to 1.0)
# ──────────────────────────────────────────────

SCORE_WEIGHTS: Dict[str, float] = {
    "cibil":               0.25,
    "foir":                0.20,
    "dpd":                 0.15,
    "credit_utilization":  0.10,
    "enquiry":             0.10,
    "employment_tenure":   0.10,
    "income_verification": 0.10,
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

FRAUD_GEO_MISMATCH_CODE: str = "FRAUD_GEO_MISMATCH"
FRAUD_MULTIPLE_APPS_CODE: str = "FRAUD_MULTIPLE_APPLICATIONS"
FRAUD_HIGH_ENQUIRY_CODE: str = "FRAUD_HIGH_ENQUIRY_COUNT"
HIGH_ENQUIRY_THRESHOLD: int = 5                     # > 5 enquiries in 6M → flag

NONE_FLAG: str = "NONE"


# ──────────────────────────────────────────────
# Reason Code Definitions
# ──────────────────────────────────────────────

REASON_CODES = {
    # Positive
    "GOOD_CIBIL":             "CIBIL score is strong (≥ 750)",
    "AVERAGE_CIBIL":          "CIBIL score is acceptable (650–749)",
    "LOW_FOIR":               "FOIR is within healthy limits (≤ 50%)",
    "MODERATE_FOIR":          "FOIR is moderate (51–65%)",
    "NO_DPD":                 "No DPD 90+ delinquencies",
    "LOW_CREDIT_UTILIZATION": "Credit utilization is low (< 30%)",
    "STABLE_EMPLOYMENT":      "Employment tenure is stable (≥ 24 months)",
    "MODERATE_EMPLOYMENT":    "Employment tenure is moderate (12–23 months)",
    "INCOME_VERIFIED":        "Income fully verified (≥ 90%)",
    "LOW_ENQUIRIES":          "Low credit enquiry count (≤ 2)",
    "LONG_CREDIT_HISTORY":    "Long credit history (≥ 36 months)",

    # Negative
    "WEAK_CIBIL":             "CIBIL score is weak (< 700)",
    "HIGH_FOIR":              "FOIR is elevated (> 50%)",
    "DPD_PRESENT":            "DPD 90+ delinquencies exist",
    "HIGH_CREDIT_UTILIZATION":"Credit utilization is high (≥ 70%)",
    "SHORT_EMPLOYMENT":       "Employment tenure is short (< 12 months)",
    "INCOME_MISMATCH":        "Income verification below threshold",
    "HIGH_ENQUIRIES":         "High credit enquiry count (> 5)",
    "SETTLED_ACCOUNTS":       "Settled accounts observed in bureau",
    "NPA_PRESENT":            "NPA / write-off found",
}
