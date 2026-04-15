"""
models.py
---------
Pydantic data models for Risk Scoring Engine input/output validation.
Ensures type safety and clean API contracts across the system.
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional
from enum import Enum


# ──────────────────────────────────────────────
# Enums
# ──────────────────────────────────────────────

class EmploymentType(str, Enum):
    SALARIED = "salaried"
    SELF_EMPLOYED = "self_employed"
    BUSINESS = "business"
    FREELANCER = "freelancer"
    UNEMPLOYED = "unemployed"


class RiskBand(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    VERY_HIGH = "VERY_HIGH"


class Decision(str, Enum):
    APPROVE = "APPROVE"
    REDUCE = "REDUCE"
    REVIEW = "REVIEW"
    DECLINE = "DECLINE"


# ──────────────────────────────────────────────
# Input Models
# ──────────────────────────────────────────────

class CustomerProfile(BaseModel):
    age: int = Field(..., ge=18, le=75, description="Age of the applicant")
    employment_type: EmploymentType
    monthly_income: float = Field(..., gt=0, description="Gross monthly income in INR")
    employment_tenure_months: int = Field(..., ge=0, description="Months at current employer")


class LoanRequest(BaseModel):
    amount: float = Field(..., gt=0, description="Requested loan amount in INR")
    tenure_months: int = Field(..., gt=0, le=360, description="Loan repayment tenure")
    declared_emi_capacity: float = Field(..., ge=0, description="Applicant-declared max EMI")


class Liabilities(BaseModel):
    existing_emis: float = Field(default=0.0, ge=0, description="Sum of all existing EMIs")
    credit_card_outstanding: float = Field(default=0.0, ge=0, description="Outstanding CC balance")


class BureauData(BaseModel):
    cibil_score: int = Field(..., ge=300, le=900, description="CIBIL credit score")
    dpd_90_plus_count: int = Field(default=0, ge=0, description="DPD 90+ instances in history")
    enquiry_last_6_months: int = Field(default=0, ge=0, description="Credit enquiries in last 6M")
    credit_utilization: float = Field(..., ge=0, le=100, description="Credit utilization percentage")
    has_npa: bool = Field(default=False, description="NPA or write-off present")
    has_settled_accounts: bool = Field(default=False, description="Settled accounts in history")
    credit_history_months: int = Field(default=0, ge=0, description="Length of credit history")


class Verification(BaseModel):
    income_match_percent: float = Field(..., ge=0, le=100, description="Income verification match %")
    age_mismatch_flag: bool = Field(default=False, description="Video age vs declared mismatch")


class FraudSignals(BaseModel):
    geo_mismatch: bool = Field(default=False, description="Geo location mismatch detected")
    multiple_applications: bool = Field(default=False, description="Duplicate applications found")


class LoanApplicationInput(BaseModel):
    """Complete input schema for a loan application."""
    customer_profile: CustomerProfile
    loan_request: LoanRequest
    liabilities: Liabilities
    bureau: BureauData
    verification: Verification
    fraud_signals: FraudSignals


# ──────────────────────────────────────────────
# Computed / Intermediate Models
# ──────────────────────────────────────────────

class ComputedFeatures(BaseModel):
    """Intermediate computed features used in scoring."""
    proposed_emi: float
    foir: float
    foir_label: str                   # "GOOD" / "RISKY" / "DECLINE"
    normalized_cibil: float           # 0–1000
    normalized_foir: float            # 0–1000
    normalized_dpd: float             # 0–1000
    normalized_utilization: float     # 0–1000
    normalized_enquiry: float         # 0–1000
    normalized_tenure: float          # 0–1000
    normalized_income_verification: float  # 0–1000


class HardDeclineResult(BaseModel):
    """Result of the hard-rules policy engine."""
    is_declined: bool
    triggered_rules: List[str]


# ──────────────────────────────────────────────
# Output Models
# ──────────────────────────────────────────────

class RiskScoreOutput(BaseModel):
    """Final risk scoring output returned to caller."""
    risk_score: int = Field(..., ge=0, le=1000)
    risk_band: RiskBand
    decision: Decision
    foir: float
    flags: List[str]
    reason_codes: List[str]
    top_factors: List[str]            # Top 3 scoring factors
    llm_explanation: str              # Natural language explanation

    class Config:
        use_enum_values = True


class AuditRecord(BaseModel):
    """Full audit trail record stored in MongoDB."""
    application_id: str
    timestamp: str
    input_data: dict
    computed_features: dict
    hard_decline_result: dict
    output: dict
