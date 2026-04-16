"""
utils.py
--------
Utility helpers: EMI calculation, ID generation, logging setup,
and natural language explanation generation.
"""

import math
import uuid
import logging
import json
from datetime import datetime, timezone
from typing import Any, Dict

from .config import ANNUAL_INTEREST_RATE


# ──────────────────────────────────────────────
# Logging Setup
# ──────────────────────────────────────────────

def setup_logger(name: str = "risk_engine") -> logging.Logger:
    """Configure and return a structured logger."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)
        handler = logging.StreamHandler()
        handler.setLevel(logging.DEBUG)
        fmt = logging.Formatter(
            "[%(asctime)s] %(levelname)-8s %(name)s — %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(fmt)
        logger.addHandler(handler)
    return logger


logger = setup_logger()


# ──────────────────────────────────────────────
# Financial Utilities
# ──────────────────────────────────────────────

def calculate_emi(principal: float, tenure_months: int,
                  annual_rate: float = ANNUAL_INTEREST_RATE) -> float:
    """
    Compute EMI using the standard reducing-balance formula.

    EMI = P * r * (1+r)^n / ((1+r)^n - 1)
    where r = monthly interest rate, n = tenure in months.

    Falls back to simple division if rate is 0.
    """
    if principal <= 0 or tenure_months <= 0:
        return 0.0

    monthly_rate = annual_rate / 12.0

    if monthly_rate == 0:
        return principal / tenure_months

    factor = math.pow(1 + monthly_rate, tenure_months)
    emi = principal * monthly_rate * factor / (factor - 1)
    return round(emi, 2)


def clamp(value: float, min_val: float = 0.0, max_val: float = 1000.0) -> float:
    """Clamp a value to [min_val, max_val]."""
    return max(min_val, min(max_val, value))


def linear_scale(value: float, low: float, high: float,
                 invert: bool = False) -> float:
    """
    Linearly scale `value` in [low, high] to [0, 1000].

    Args:
        invert: If True, lower value → higher score (e.g., FOIR, DPD).
    """
    if high == low:
        return 0.0
    ratio = (value - low) / (high - low)
    ratio = clamp(ratio, 0.0, 1.0)
    score = (1.0 - ratio) * 1000 if invert else ratio * 1000
    return round(clamp(score), 2)


# ──────────────────────────────────────────────
# ID & Timestamp Utilities
# ──────────────────────────────────────────────

def generate_application_id() -> str:
    """Generate a deterministic-looking unique application ID."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    uid = str(uuid.uuid4()).split("-")[0].upper()
    return f"APP-{ts}-{uid}"


def utc_now_iso() -> str:
    """Return current UTC timestamp as ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()


# ──────────────────────────────────────────────
# Serialisation helpers
# ──────────────────────────────────────────────

def to_serialisable(obj: Any) -> Any:
    """Recursively convert Pydantic models / dataclasses to plain dicts."""
    if hasattr(obj, "dict"):
        return obj.dict()
    if isinstance(obj, dict):
        return {k: to_serialisable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [to_serialisable(i) for i in obj]
    return obj


def pretty_json(data: Dict) -> str:
    """Return pretty-printed JSON string."""
    return json.dumps(data, indent=2, default=str)


# ──────────────────────────────────────────────
# LLM-Ready Natural Language Explanation
# ──────────────────────────────────────────────

_TEMPLATES = {
    # Decision → template tokens
    "APPROVE": (
        "This applicant presents a {risk_band_adj} risk profile. "
        "{positive_summary} "
        "Based on the scoring analysis, we recommend full loan approval."
    ),
    "REDUCE": (
        "This applicant shows a moderate risk profile. "
        "{positive_summary} "
        "However, {negative_summary} "
        "We recommend approving a reduced loan amount to mitigate exposure."
    ),
    "REVIEW": (
        "This applicant carries elevated risk and requires manual review. "
        "{negative_summary} "
        "A credit analyst should evaluate the application before a decision is made."
    ),
    "DECLINE": (
        "This application has been declined. "
        "{negative_summary} "
        "The applicant does not meet the minimum credit policy requirements at this time."
    ),
}

_POSITIVE_PHRASES = {
    "GOOD_CIBIL":             "strong credit score",
    "AVERAGE_CIBIL":          "acceptable credit score",
    "LOW_FOIR":               "manageable debt obligations",
    "MODERATE_FOIR":          "moderate debt load",
    "NO_DPD":                 "clean repayment history",
    "LOW_CREDIT_UTILIZATION": "low credit utilization",
    "STABLE_EMPLOYMENT":      "stable employment history",
    "MODERATE_EMPLOYMENT":    "reasonable employment track record",
    "INCOME_VERIFIED":        "verified income",
    "LOW_ENQUIRIES":          "minimal recent credit enquiries",
    "LONG_CREDIT_HISTORY":    "a long credit history",
}

_NEGATIVE_PHRASES = {
    "WEAK_CIBIL":              "a weak credit score",
    "HIGH_FOIR":               "high existing debt obligations",
    "DPD_PRESENT":             "past delinquencies on record",
    "HIGH_CREDIT_UTILIZATION": "high credit card utilization",
    "SHORT_EMPLOYMENT":        "limited employment history",
    "INCOME_MISMATCH":         "unverified or mismatched income",
    "HIGH_ENQUIRIES":          "a high number of recent credit enquiries",
    "SETTLED_ACCOUNTS":        "settled accounts in credit history",
    "NPA_PRESENT":             "a non-performing asset on record",
    "FRAUD_GEO_MISMATCH":      "geographic inconsistencies",
    "FRAUD_MULTIPLE_APPLICATIONS": "multiple simultaneous applications detected",
    "FRAUD_HIGH_ENQUIRY_COUNT": "suspicious enquiry activity",
    "FOIR_DECLINE":            "FOIR exceeding policy limits",
    "CIBIL_BELOW_MINIMUM":     "CIBIL score below minimum threshold",
    "INCOME_VERIFICATION_LOW": "insufficient income verification",
    "DPD_EXCESSIVE":           "excessive DPD delinquency count",
    "NPA_WRITEOFF":            "presence of NPA/write-off in bureau",
}


def generate_explanation(decision: str, risk_band: str,
                         reason_codes: list, flags: list) -> str:
    """
    Build a concise, LLM-ready natural language explanation.

    Combines positive and negative signal phrases into a human-readable
    summary sentence suitable for display or downstream LLM processing.
    """
    template = _TEMPLATES.get(decision, _TEMPLATES["REVIEW"])

    positives = [
        _POSITIVE_PHRASES[rc] for rc in reason_codes
        if rc in _POSITIVE_PHRASES
    ]
    negatives = [
        _NEGATIVE_PHRASES[rc] for rc in reason_codes
        if rc in _NEGATIVE_PHRASES
    ] + [
        _NEGATIVE_PHRASES[f] for f in flags
        if f in _NEGATIVE_PHRASES
    ]

    risk_band_adj_map = {
        "LOW": "low", "MEDIUM": "moderate",
        "HIGH": "high", "VERY_HIGH": "very high",
    }
    risk_band_adj = risk_band_adj_map.get(risk_band, "moderate")

    positive_summary = (
        f"The applicant demonstrates {_oxford_join(positives)}."
        if positives else "The applicant shows acceptable creditworthiness."
    )
    negative_summary = (
        f"There are concerns around {_oxford_join(negatives)}."
        if negatives else "There are minor risk factors to note."
    )

    return template.format(
        risk_band_adj=risk_band_adj,
        positive_summary=positive_summary,
        negative_summary=negative_summary,
    )


def _oxford_join(items: list) -> str:
    """Join list items with Oxford comma style."""
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return ", ".join(items[:-1]) + f", and {items[-1]}"
