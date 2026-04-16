"""
main.py
-------
CLI runner that executes multiple test-case scenarios through the
Risk Scoring Engine and prints formatted, colour-coded results.

Usage:
    python main.py              # Run all built-in test cases
    python main.py --save-db    # Also persist results to MongoDB
    python main.py --json-only  # Raw JSON output only
"""

import argparse
import json
import sys
import io
from typing import List, Dict

# Force UTF-8 stdout on Windows so ANSI codes don't cause encode errors.
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from .risk_engine import score_application
from .utils import pretty_json, logger


# ─────────────────────────────────────────────────────────
# Shared location_signals helper (reused across test cases)
# ─────────────────────────────────────────────────────────

def _loc(ip_state="Karnataka", kyc_state="Karnataka",
         ip_country="IN", kyc_country="IN", vpn=False) -> dict:
    return {
        "ip_country": ip_country,
        "ip_state": ip_state,
        "kyc_country": kyc_country,
        "kyc_state": kyc_state,
        "vpn_or_proxy_detected": vpn,
    }


# ─────────────────────────────────────────────────────────
# Test Cases  (10 curated scenarios covering all code paths)
# ─────────────────────────────────────────────────────────

TEST_CASES: List[Dict] = [
    # ── TC-01 : Ideal Applicant ─────────────────────────────────────────────
    {
        "_name": "TC-01 | Ideal Applicant (Strong Approval)",
        "customer_profile": {
            "age": 32,
            "employment_type": "salaried",
            "monthly_income": 80000,
            "employment_tenure_months": 48,
        },
        "loan_request": {"amount": 200000, "tenure_months": 36, "declared_emi_capacity": 8000},
        "liabilities": {"existing_emis": 5000, "credit_card_outstanding": 10000},
        "bureau": {
            "cibil_score": 790, "dpd_90_plus_count": 0, "enquiry_last_6_months": 1,
            "credit_utilization": 12, "has_npa": False, "has_settled_accounts": False,
            "credit_history_months": 72,
        },
        "verification": {"income_match_percent": 95, "age_mismatch_flag": False},
        "fraud_signals": {"geo_mismatch": False, "multiple_applications": False},
        "location_signals": _loc(),
        "collateral": None,
    },

    # ── TC-02 : Moderate FOIR ───────────────────────────────────────────────
    {
        "_name": "TC-02 | Sample from Spec (Moderate FOIR)",
        "customer_profile": {
            "age": 29,
            "employment_type": "salaried",
            "monthly_income": 60000,
            "employment_tenure_months": 18,
        },
        "loan_request": {"amount": 300000, "tenure_months": 36, "declared_emi_capacity": 12000},
        "liabilities": {"existing_emis": 15000, "credit_card_outstanding": 40000},
        "bureau": {
            "cibil_score": 720, "dpd_90_plus_count": 0, "enquiry_last_6_months": 2,
            "credit_utilization": 25, "has_npa": False, "has_settled_accounts": False,
            "credit_history_months": 48,
        },
        "verification": {"income_match_percent": 90, "age_mismatch_flag": False},
        "fraud_signals": {"geo_mismatch": False, "multiple_applications": False},
        "location_signals": _loc(),
        "collateral": None,
    },

    # ── TC-03 : High FOIR → Hard Decline ───────────────────────────────────
    {
        "_name": "TC-03 | High FOIR (Hard Decline)",
        "customer_profile": {
            "age": 35,
            "employment_type": "salaried",
            "monthly_income": 40000,
            "employment_tenure_months": 24,
        },
        "loan_request": {"amount": 500000, "tenure_months": 60, "declared_emi_capacity": 5000},
        "liabilities": {"existing_emis": 20000, "credit_card_outstanding": 80000},
        "bureau": {
            "cibil_score": 680, "dpd_90_plus_count": 1, "enquiry_last_6_months": 3,
            "credit_utilization": 60, "has_npa": False, "has_settled_accounts": False,
            "credit_history_months": 36,
        },
        "verification": {"income_match_percent": 85, "age_mismatch_flag": False},
        "fraud_signals": {"geo_mismatch": False, "multiple_applications": False},
        "location_signals": _loc(),
        "collateral": None,
    },

    # ── TC-04 : NPA Present → Hard Decline ─────────────────────────────────
    {
        "_name": "TC-04 | NPA Present (Hard Decline)",
        "customer_profile": {
            "age": 45,
            "employment_type": "self_employed",
            "monthly_income": 90000,
            "employment_tenure_months": 120,
        },
        "loan_request": {"amount": 600000, "tenure_months": 48, "declared_emi_capacity": 20000},
        "liabilities": {"existing_emis": 10000, "credit_card_outstanding": 5000},
        "bureau": {
            "cibil_score": 710, "dpd_90_plus_count": 0, "enquiry_last_6_months": 2,
            "credit_utilization": 20, "has_npa": True, "has_settled_accounts": True,
            "credit_history_months": 120,
        },
        "verification": {"income_match_percent": 88, "age_mismatch_flag": False},
        "fraud_signals": {"geo_mismatch": False, "multiple_applications": False},
        "location_signals": _loc(),
        "collateral": None,
    },

    # ── TC-05 : Fraud Signals → Review override ─────────────────────────────
    {
        "_name": "TC-05 | Fraud Signals + Borderline Score (Review)",
        "customer_profile": {
            "age": 27,
            "employment_type": "freelancer",
            "monthly_income": 50000,
            "employment_tenure_months": 10,
        },
        "loan_request": {"amount": 250000, "tenure_months": 36, "declared_emi_capacity": 9000},
        "liabilities": {"existing_emis": 8000, "credit_card_outstanding": 30000},
        "bureau": {
            "cibil_score": 680, "dpd_90_plus_count": 1, "enquiry_last_6_months": 6,
            "credit_utilization": 45, "has_npa": False, "has_settled_accounts": False,
            "credit_history_months": 24,
        },
        "verification": {"income_match_percent": 75, "age_mismatch_flag": False},
        "fraud_signals": {"geo_mismatch": True, "multiple_applications": True},
        "location_signals": _loc(ip_state="Maharashtra", kyc_state="Karnataka"),
        "collateral": None,
    },

    # ── TC-06 : Young Applicant → Manual Review ─────────────────────────────
    {
        "_name": "TC-06 | Young Applicant Low History (Manual Review)",
        "customer_profile": {
            "age": 22,
            "employment_type": "salaried",
            "monthly_income": 30000,
            "employment_tenure_months": 6,
        },
        "loan_request": {"amount": 100000, "tenure_months": 24, "declared_emi_capacity": 5000},
        "liabilities": {"existing_emis": 2000, "credit_card_outstanding": 5000},
        "bureau": {
            "cibil_score": 670, "dpd_90_plus_count": 0, "enquiry_last_6_months": 4,
            "credit_utilization": 55, "has_npa": False, "has_settled_accounts": False,
            "credit_history_months": 8,
        },
        "verification": {"income_match_percent": 80, "age_mismatch_flag": False},
        "fraud_signals": {"geo_mismatch": False, "multiple_applications": False},
        "location_signals": _loc(),
        "collateral": None,
    },

    # ── TC-07 : Secured Loan (Residential Property) → Approve with boost ────
    {
        "_name": "TC-07 | Secured Loan - Residential Property (Approve + Boost)",
        "customer_profile": {
            "age": 38,
            "employment_type": "salaried",
            "monthly_income": 120000,
            "employment_tenure_months": 72,
        },
        "loan_request": {"amount": 3000000, "tenure_months": 180, "declared_emi_capacity": 30000},
        "liabilities": {"existing_emis": 10000, "credit_card_outstanding": 50000},
        "bureau": {
            "cibil_score": 800, "dpd_90_plus_count": 0, "enquiry_last_6_months": 1,
            "credit_utilization": 15, "has_npa": False, "has_settled_accounts": False,
            "credit_history_months": 96,
        },
        "verification": {"income_match_percent": 98, "age_mismatch_flag": False},
        "fraud_signals": {"geo_mismatch": False, "multiple_applications": False},
        "location_signals": _loc(),
        "collateral": {
            "collateral_type": "residential_property",
            "market_value": 5000000,        # ₹50L property, loan ₹30L → LTV 60%
            "ownership_verified": True,
        },
    },

    # ── TC-08 : VPN Detected → Hard Decline ─────────────────────────────────
    {
        "_name": "TC-08 | VPN / Proxy Detected (Hard Decline)",
        "customer_profile": {
            "age": 30,
            "employment_type": "salaried",
            "monthly_income": 75000,
            "employment_tenure_months": 36,
        },
        "loan_request": {"amount": 400000, "tenure_months": 36, "declared_emi_capacity": 15000},
        "liabilities": {"existing_emis": 5000, "credit_card_outstanding": 20000},
        "bureau": {
            "cibil_score": 760, "dpd_90_plus_count": 0, "enquiry_last_6_months": 2,
            "credit_utilization": 20, "has_npa": False, "has_settled_accounts": False,
            "credit_history_months": 60,
        },
        "verification": {"income_match_percent": 92, "age_mismatch_flag": False},
        "fraud_signals": {"geo_mismatch": False, "multiple_applications": False},
        "location_signals": _loc(vpn=True),    # VPN → hard decline regardless of score
        "collateral": None,
    },

    # ── TC-09 : Overseas IP → Fraud Flag → Review ───────────────────────────
    {
        "_name": "TC-09 | Overseas IP Country Mismatch (Fraud Flag -> Review)",
        "customer_profile": {
            "age": 34,
            "employment_type": "salaried",
            "monthly_income": 90000,
            "employment_tenure_months": 24,
        },
        "loan_request": {"amount": 500000, "tenure_months": 48, "declared_emi_capacity": 18000},
        "liabilities": {"existing_emis": 8000, "credit_card_outstanding": 30000},
        "bureau": {
            "cibil_score": 740, "dpd_90_plus_count": 0, "enquiry_last_6_months": 2,
            "credit_utilization": 22, "has_npa": False, "has_settled_accounts": False,
            "credit_history_months": 54,
        },
        "verification": {"income_match_percent": 91, "age_mismatch_flag": False},
        "fraud_signals": {"geo_mismatch": False, "multiple_applications": False},
        "location_signals": _loc(
            ip_country="US", kyc_country="IN",    # Overseas IP — fraud flag
            ip_state="California", kyc_state="Karnataka",
        ),
        "collateral": None,
    },

    # ── TC-10 : Counter-offer (Income insufficient for requested amount) ─────
    {
        "_name": "TC-10 | Counter-offer Generated (Income Too Low for Requested)",
        "customer_profile": {
            "age": 31,
            "employment_type": "salaried",
            "monthly_income": 35000,
            "employment_tenure_months": 30,
        },
        "loan_request": {
            "amount": 1500000,         # ₹15L requested — way beyond FOIR headroom
            "tenure_months": 60,
            "declared_emi_capacity": 10000,
        },
        "liabilities": {"existing_emis": 8000, "credit_card_outstanding": 20000},
        "bureau": {
            "cibil_score": 730, "dpd_90_plus_count": 0, "enquiry_last_6_months": 2,
            "credit_utilization": 28, "has_npa": False, "has_settled_accounts": False,
            "credit_history_months": 48,
        },
        "verification": {"income_match_percent": 88, "age_mismatch_flag": False},
        "fraud_signals": {"geo_mismatch": False, "multiple_applications": False},
        "location_signals": _loc(),
        "collateral": None,
    },

    # ── TC-11 : Thin File / No Bureau History ────────────────────────────────
    {
        "_name": "TC-11 | Thin File No Bureau History (Review)",
        "customer_profile": {
            "age": 25,
            "employment_type": "salaried",
            "monthly_income": 35000,
            "employment_tenure_months": 14,
        },
        "loan_request": {"amount": 150000, "tenure_months": 24, "declared_emi_capacity": 7000},
        "liabilities": {"existing_emis": 0, "credit_card_outstanding": 0},
        "bureau": {
            "cibil_score": 0,
            "dpd_90_plus_count": 0,
            "enquiry_last_6_months": 0,
            "credit_utilization": 0,
            "has_npa": False,
            "has_settled_accounts": False,
            "credit_history_months": 0,
        },
        "verification": {"income_match_percent": 85, "age_mismatch_flag": False},
        "fraud_signals": {"geo_mismatch": False, "multiple_applications": False},
        "location_signals": _loc(),
        "collateral": None,
    },

    # ── TC-12 : Settled Account with Good Current CIBIL ──────────────────────
    {
        "_name": "TC-12 | Settled Account Good Recovery (Reduce with Discount)",
        "customer_profile": {
            "age": 36,
            "employment_type": "salaried",
            "monthly_income": 70000,
            "employment_tenure_months": 40,
        },
        "loan_request": {"amount": 400000, "tenure_months": 36, "declared_emi_capacity": 14000},
        "liabilities": {"existing_emis": 8000, "credit_card_outstanding": 15000},
        "bureau": {
            "cibil_score": 730,
            "dpd_90_plus_count": 0,
            "enquiry_last_6_months": 1,
            "credit_utilization": 20,
            "has_npa": False,
            "has_settled_accounts": True,
            "credit_history_months": 60,
        },
        "verification": {"income_match_percent": 92, "age_mismatch_flag": False},
        "fraud_signals": {"geo_mismatch": False, "multiple_applications": False},
        "location_signals": _loc(),
        "collateral": None,
    },

    # ── TC-13 : Age Mismatch Flag from Video KYC ─────────────────────────────
    {
        "_name": "TC-13 | Age Mismatch from Video KYC (Review)",
        "customer_profile": {
            "age": 45,
            "employment_type": "salaried",
            "monthly_income": 85000,
            "employment_tenure_months": 60,
        },
        "loan_request": {"amount": 500000, "tenure_months": 48, "declared_emi_capacity": 18000},
        "liabilities": {"existing_emis": 12000, "credit_card_outstanding": 20000},
        "bureau": {
            "cibil_score": 755,
            "dpd_90_plus_count": 0,
            "enquiry_last_6_months": 2,
            "credit_utilization": 18,
            "has_npa": False,
            "has_settled_accounts": False,
            "credit_history_months": 84,
        },
        "verification": {"income_match_percent": 93, "age_mismatch_flag": True},
        "fraud_signals": {"geo_mismatch": False, "multiple_applications": False},
        "location_signals": _loc(),
        "collateral": None,
    },
]


# ─────────────────────────────────────────────────────────
# ANSI Colour Helpers  (ASCII-only strings)
# ─────────────────────────────────────────────────────────

_RESET  = "\033[0m"
_BOLD   = "\033[1m"
_GREEN  = "\033[92m"
_YELLOW = "\033[93m"
_ORANGE = "\033[33m"
_RED    = "\033[91m"
_CYAN   = "\033[96m"
_GREY   = "\033[90m"
_BLUE   = "\033[94m"

_DECISION_COLOUR = {
    "APPROVE": _GREEN,
    "REDUCE":  _YELLOW,
    "REVIEW":  _ORANGE,
    "DECLINE": _RED,
}
_BAND_COLOUR = {
    "LOW":       _GREEN,
    "MEDIUM":    _YELLOW,
    "HIGH":      _ORANGE,
    "VERY_HIGH": _RED,
}

SEP  = "=" * 70
DASH = "-" * 70


def _c(text: str, colour: str) -> str:
    return f"{colour}{text}{_RESET}"


def _fmt_inr(amount: float) -> str:
    """Format a number as Indian Rupees."""
    if amount < 0:
        return "N/A (unsecured)"
    return f"Rs {amount:,.0f}"


def _print_result(name: str, result: dict, idx: int) -> None:
    """Pretty-print a single test case result to stdout."""
    decision  = result.get("decision", "UNKNOWN")
    band      = result.get("risk_band", "UNKNOWN")
    score     = result.get("risk_score", 0)
    foir_pct  = result.get("foir", 0) * 100
    elig      = result.get("eligibility", {})

    dcol = _DECISION_COLOUR.get(decision, _RESET)
    bcol = _BAND_COLOUR.get(band, _RESET)

    print(f"\n{_BOLD}{_CYAN}{SEP}{_RESET}")
    print(f"  {_BOLD}[{idx}] {name}{_RESET}")
    print(DASH)
    print(f"  {'Risk Score':28s}: {_BOLD}{score:>4d} / 1000{_RESET}")
    print(f"  {'Risk Band':28s}: {_c(band, bcol)}")
    print(f"  {'Decision':28s}: {_c(decision, dcol)}")
    print(f"  {'FOIR':28s}: {foir_pct:.1f}%")
    print(f"  {'Max Eligible (Income)':28s}: {_fmt_inr(elig.get('max_income_eligible', 0))}")
    print(f"  {'Max Eligible (Collateral)':28s}: {_fmt_inr(elig.get('max_collateral_eligible', -1))}")
    print(f"  {'Final Max Eligible':28s}: {_c(_fmt_inr(elig.get('final_max_eligible', 0)), _BLUE)}")

    if elig.get("is_counter_offer"):
        co = elig.get("counter_offer_amount")
        co_str = _fmt_inr(co) if co else "None (below minimum)"
        print(f"  {'Counter-Offer':28s}: {_c(co_str, _YELLOW)}")
        
    _guard_key = getattr(_print_result, "last_idx", None)
    if _guard_key != idx:
        print(f"  {'Flags':28s}: {', '.join(result.get('flags', ['NONE']))}")
        print(f"  {'Top Factors':28s}: {', '.join(result.get('top_factors', []))}")
        print(f"  {'Reason Codes':28s}: {', '.join(result.get('reason_codes', []))}")
        print(f"\n  {_GREY}[Explanation]{_RESET}")

        explanation = result.get("llm_explanation", "N/A")
        line = "  "
        for word in explanation.split():
            if len(line) + len(word) + 1 > 68:
                print(line)
                line = "  " + word + " "
            else:
                line += word + " "
        if line.strip():
            print(line)
        print()
        setattr(_print_result, "last_idx", idx)


# ─────────────────────────────────────────────────────────
# Main Runner
# ─────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Risk Scoring Engine - Loan Origination System (v2)"
    )
    parser.add_argument(
        "--save-db",
        action="store_true",
        help="Enable MongoDB persistence (requires local MongoDB on port 27017)",
    )
    parser.add_argument(
        "--json-only",
        action="store_true",
        help="Suppress coloured output; print raw JSON results only",
    )
    args = parser.parse_args()

    if not args.json_only:
        print(f"\n{_BOLD}{_CYAN}{SEP}")
        print("  RISK SCORING ENGINE v2  --  LOAN ORIGINATION SYSTEM")
        print("  Features: CIBIL | FOIR | DPD | Utilisation | Enquiry |")
        print("            Tenure | Income | Age | Location | Collateral")
        print(f"{SEP}{_RESET}\n")
        print(f"  Running {len(TEST_CASES)} test case(s) ...\n")

    all_results: List[dict] = []

    for idx, tc in enumerate(TEST_CASES, start=1):
        name = tc.pop("_name", f"Test Case {idx}")
        try:
            result = score_application(tc)
            all_results.append({"test_case": name, "result": result})

            if args.json_only:
                print(pretty_json(result))
            else:
                _print_result(name, result, idx)

        except Exception as exc:
            logger.error(
                "Test case [%d] '%s' failed: %s", idx, name, exc, exc_info=True
            )
            print(f"  {_RED}ERROR [{idx}] {name}: {exc}{_RESET}\n")

    # ── Summary Table ───────────────────────────────────────────────────────
    if not args.json_only:
        print(f"\n{_BOLD}{DASH}")
        print(f"  {'#':<4} {'Test Case':<40} {'Score':>5}  {'Eligible':>12}  Decision")
        print(f"{DASH}{_RESET}")
        for i, entry in enumerate(all_results, start=1):
            r       = entry["result"]
            dec     = r.get("decision", "?")
            score   = r.get("risk_score", 0)
            label   = entry["test_case"][:38]
            eligible = r.get("eligibility", {}).get("final_max_eligible", 0)
            dcol    = _DECISION_COLOUR.get(dec, _RESET)
            print(
                f"  {i:<4} {label:<40} {score:>5}  "
                f"{_fmt_inr(eligible):>12}  {_c(dec, dcol)}"
            )
        print(f"{_BOLD}{DASH}{_RESET}\n")

    if not args.save_db and not args.json_only:
        print(
            f"  {_GREY}[i] MongoDB persistence disabled. "
            f"Run with --save-db to persist results.{_RESET}\n"
        )


if __name__ == "__main__":
    main()
