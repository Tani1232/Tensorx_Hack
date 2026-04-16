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
    SALARIED      = "salaried"
    SELF_EMPLOYED = "self_employed"
    BUSINESS      = "business"
    FREELANCER    = "freelancer"
    UNEMPLOYED    = "unemployed"


class CollateralType(str, Enum):
    RESIDENTIAL_PROPERTY = "residential_property"
    COMMERCIAL_PROPERTY  = "commercial_property"
    GOLD                 = "gold"
    FIXED_DEPOSIT        = "fixed_deposit"
    STOCKS_MF            = "stocks_mf"
    NONE                 = "none"


class RiskBand(str, Enum):
    LOW       = "LOW"
    MEDIUM    = "MEDIUM"
    HIGH      = "HIGH"
    VERY_HIGH = "VERY_HIGH"


class Decision(str, Enum):
    APPROVE = "APPROVE"
    REDUCE  = "REDUCE"
    REVIEW  = "REVIEW"
    DECLINE = "DECLINE"


# ──────────────────────────────────────────────
# Input Models
# ──────────────────────────────────────────────

class CustomerProfile(BaseModel):
    age: int = Field(..., ge=0, le=120, description="Age of the applicant")
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
    cibil_score: int = Field(..., ge=0, le=900, description="CIBIL credit score")
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


class LocationSignals(BaseModel):
    """IP geolocation vs. KYC address signals for fraud detection."""
    ip_country: str = Field(..., description="2-letter country code derived from IP, e.g. 'IN'")
    ip_state: str = Field(..., description="State/province derived from IP, e.g. 'Karnataka'")
    kyc_country: str = Field(..., description="Country on KYC documents, e.g. 'IN'")
    kyc_state: str = Field(..., description="State on KYC documents, e.g. 'Karnataka'")
    vpn_or_proxy_detected: bool = Field(default=False, description="VPN / TOR / Proxy flag")


class CollateralData(BaseModel):
    """Asset offered as security for a secured loan."""
    collateral_type: CollateralType
    market_value: float = Field(..., gt=0, description="Current market value of the asset in INR")
    ownership_verified: bool = Field(default=False, description="Title deed / ownership confirmed")


class LoanApplicationInput(BaseModel):
    """Complete input schema for a loan application."""
    customer_profile: CustomerProfile
    loan_request: LoanRequest
    liabilities: Liabilities
    bureau: BureauData
    verification: Verification
    fraud_signals: FraudSignals
    location_signals: LocationSignals
    collateral: Optional[CollateralData] = None   # None = unsecured loan


# ──────────────────────────────────────────────
# Computed / Intermediate Models
# ──────────────────────────────────────────────

class ComputedFeatures(BaseModel):
    """Intermediate computed features used in scoring."""
    proposed_emi: float
    foir: float
    foir_label: str                        # "GOOD" / "RISKY" / "DECLINE"

    # Core normalised scores (0–1000 each)
    normalized_cibil: float
    normalized_foir: float
    normalized_dpd: float
    normalized_utilization: float
    normalized_enquiry: float
    normalized_tenure: float
    normalized_income_verification: float

    # New normalised scores (0–1000 each)
    normalized_age: float
    normalized_location: float
    normalized_collateral: float

    # Collateral / eligibility extras
    ltv_ratio: Optional[float] = None       # None for unsecured loans
    max_income_eligible: float = 0.0
    max_collateral_eligible: float = 0.0
    final_max_eligible: float = 0.0
    is_counter_offer: bool = False
    counter_offer_amount: Optional[float] = None


class HardDeclineResult(BaseModel):
    """Result of the hard-rules policy engine."""
    is_declined: bool
    triggered_rules: List[str]


# ──────────────────────────────────────────────
# Output Models
# ──────────────────────────────────────────────

class EligibilityResult(BaseModel):
    """Loan eligibility details attached to final output."""
    max_income_eligible: float
    max_collateral_eligible: float          # float('inf') rendered as -1 for unsecured
    final_max_eligible: float
    is_counter_offer: bool
    counter_offer_amount: Optional[float]


class RiskScoreOutput(BaseModel):
    """Final risk scoring output returned to caller."""
    risk_score: int = Field(..., ge=0, le=1000)
    risk_band: RiskBand
    decision: Decision
    foir: float
    flags: List[str]
    reason_codes: List[str]
    top_factors: List[str]                 # Top 3 scoring factors
    llm_explanation: str                   # Natural language explanation
    eligibility: EligibilityResult         # Loan eligibility details

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
