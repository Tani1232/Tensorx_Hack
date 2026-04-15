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
# Falls back to ASCII-safe 'replace' for any remaining stray bytes.
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from risk_engine import score_application
from utils import pretty_json, logger


# ─────────────────────────────────────────────────────────
# Test Cases  (6 curated scenarios covering all code paths)
# ─────────────────────────────────────────────────────────

TEST_CASES: List[Dict] = [
    {
        "_name": "TC-01 | Ideal Applicant (Strong Approval)",
        "customer_profile": {
            "age": 32,
            "employment_type": "salaried",
            "monthly_income": 80000,
            "employment_tenure_months": 48,
        },
        "loan_request": {
            "amount": 200000,
            "tenure_months": 36,
            "declared_emi_capacity": 8000,
        },
        "liabilities": {
            "existing_emis": 5000,
            "credit_card_outstanding": 10000,
        },
        "bureau": {
            "cibil_score": 790,
            "dpd_90_plus_count": 0,
            "enquiry_last_6_months": 1,
            "credit_utilization": 12,
            "has_npa": False,
            "has_settled_accounts": False,
            "credit_history_months": 72,
        },
        "verification": {"income_match_percent": 95, "age_mismatch_flag": False},
        "fraud_signals": {"geo_mismatch": False, "multiple_applications": False},
    },
    {
        "_name": "TC-02 | Sample from Spec (Moderate FOIR)",
        "customer_profile": {
            "age": 29,
            "employment_type": "salaried",
            "monthly_income": 60000,
            "employment_tenure_months": 18,
        },
        "loan_request": {
            "amount": 300000,
            "tenure_months": 36,
            "declared_emi_capacity": 12000,
        },
        "liabilities": {
            "existing_emis": 15000,
            "credit_card_outstanding": 40000,
        },
        "bureau": {
            "cibil_score": 720,
            "dpd_90_plus_count": 0,
            "enquiry_last_6_months": 2,
            "credit_utilization": 25,
            "has_npa": False,
            "has_settled_accounts": False,
            "credit_history_months": 48,
        },
        "verification": {"income_match_percent": 90, "age_mismatch_flag": False},
        "fraud_signals": {"geo_mismatch": False, "multiple_applications": False},
    },
    {
        "_name": "TC-03 | High FOIR (Hard Decline)",
        "customer_profile": {
            "age": 35,
            "employment_type": "salaried",
            "monthly_income": 40000,
            "employment_tenure_months": 24,
        },
        "loan_request": {
            "amount": 500000,
            "tenure_months": 60,
            "declared_emi_capacity": 5000,
        },
        "liabilities": {"existing_emis": 20000, "credit_card_outstanding": 80000},
        "bureau": {
            "cibil_score": 680,
            "dpd_90_plus_count": 1,
            "enquiry_last_6_months": 3,
            "credit_utilization": 60,
            "has_npa": False,
            "has_settled_accounts": False,
            "credit_history_months": 36,
        },
        "verification": {"income_match_percent": 85, "age_mismatch_flag": False},
        "fraud_signals": {"geo_mismatch": False, "multiple_applications": False},
    },
    {
        "_name": "TC-04 | NPA Present (Hard Decline)",
        "customer_profile": {
            "age": 45,
            "employment_type": "self_employed",
            "monthly_income": 90000,
            "employment_tenure_months": 120,
        },
        "loan_request": {
            "amount": 600000,
            "tenure_months": 48,
            "declared_emi_capacity": 20000,
        },
        "liabilities": {"existing_emis": 10000, "credit_card_outstanding": 5000},
        "bureau": {
            "cibil_score": 710,
            "dpd_90_plus_count": 0,
            "enquiry_last_6_months": 2,
            "credit_utilization": 20,
            "has_npa": True,              # Hard decline trigger
            "has_settled_accounts": True,
            "credit_history_months": 120,
        },
        "verification": {"income_match_percent": 88, "age_mismatch_flag": False},
        "fraud_signals": {"geo_mismatch": False, "multiple_applications": False},
    },
    {
        "_name": "TC-05 | Fraud Signals + Borderline Score (Review)",
        "customer_profile": {
            "age": 27,
            "employment_type": "freelancer",
            "monthly_income": 50000,
            "employment_tenure_months": 10,
        },
        "loan_request": {
            "amount": 250000,
            "tenure_months": 36,
            "declared_emi_capacity": 9000,
        },
        "liabilities": {"existing_emis": 8000, "credit_card_outstanding": 30000},
        "bureau": {
            "cibil_score": 680,
            "dpd_90_plus_count": 1,
            "enquiry_last_6_months": 6,   # Fraud: high enquiry count
            "credit_utilization": 45,
            "has_npa": False,
            "has_settled_accounts": False,
            "credit_history_months": 24,
        },
        "verification": {"income_match_percent": 75, "age_mismatch_flag": False},
        "fraud_signals": {
            "geo_mismatch": True,          # Fraud flag
            "multiple_applications": True, # Fraud flag
        },
    },
    {
        "_name": "TC-06 | Young Applicant Low History (Manual Review)",
        "customer_profile": {
            "age": 22,
            "employment_type": "salaried",
            "monthly_income": 30000,
            "employment_tenure_months": 6,
        },
        "loan_request": {
            "amount": 100000,
            "tenure_months": 24,
            "declared_emi_capacity": 5000,
        },
        "liabilities": {"existing_emis": 2000, "credit_card_outstanding": 5000},
        "bureau": {
            "cibil_score": 670,
            "dpd_90_plus_count": 0,
            "enquiry_last_6_months": 4,
            "credit_utilization": 55,
            "has_npa": False,
            "has_settled_accounts": False,
            "credit_history_months": 8,
        },
        "verification": {"income_match_percent": 80, "age_mismatch_flag": False},
        "fraud_signals": {"geo_mismatch": False, "multiple_applications": False},
    },
]


# ─────────────────────────────────────────────────────────
# ANSI Colour Helpers  (ASCII-only strings; no Unicode)
# ─────────────────────────────────────────────────────────

_RESET  = "\033[0m"
_BOLD   = "\033[1m"
_GREEN  = "\033[92m"
_YELLOW = "\033[93m"
_ORANGE = "\033[33m"
_RED    = "\033[91m"
_CYAN   = "\033[96m"
_GREY   = "\033[90m"

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

SEP  = "=" * 70   # section separator
DASH = "-" * 70   # sub-separator


def _c(text: str, colour: str) -> str:
    """Wrap text in an ANSI colour code."""
    return f"{colour}{text}{_RESET}"


def _print_result(name: str, result: dict, idx: int) -> None:
    """Pretty-print a single test case result to stdout."""
    decision = result.get("decision", "UNKNOWN")
    band     = result.get("risk_band", "UNKNOWN")
    score    = result.get("risk_score", 0)
    foir_pct = result.get("foir", 0) * 100

    dcol = _DECISION_COLOUR.get(decision, _RESET)
    bcol = _BAND_COLOUR.get(band, _RESET)

    print(f"\n{_BOLD}{_CYAN}{SEP}{_RESET}")
    print(f"  {_BOLD}[{idx}] {name}{_RESET}")
    print(DASH)
    print(f"  {'Risk Score':25s}: {_BOLD}{score:>4d} / 1000{_RESET}")
    print(f"  {'Risk Band':25s}: {_c(band, bcol)}")
    print(f"  {'Decision':25s}: {_c(decision, dcol)}")
    print(f"  {'FOIR':25s}: {foir_pct:.1f}%")
    print(f"  {'Flags':25s}: {', '.join(result.get('flags', ['NONE']))}")
    print(f"  {'Top Factors':25s}: {', '.join(result.get('top_factors', []))}")
    print(f"  {'Reason Codes':25s}: {', '.join(result.get('reason_codes', []))}")
    print(f"\n  {_GREY}[Explanation]{_RESET}")

    # Word-wrap explanation at 68 chars
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


# ─────────────────────────────────────────────────────────
# Main Runner
# ─────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Risk Scoring Engine - Loan Origination System"
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
        print("  RISK SCORING ENGINE  --  LOAN ORIGINATION SYSTEM")
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

    # ── Summary Table ─────────────────────────────────────────────────────
    if not args.json_only:
        print(f"\n{_BOLD}{DASH}")
        print(f"  {'#':<4} {'Test Case':<44} {'Score':>5}  Decision")
        print(f"{DASH}{_RESET}")
        for i, entry in enumerate(all_results, start=1):
            r      = entry["result"]
            dec    = r.get("decision", "?")
            score  = r.get("risk_score", 0)
            label  = entry["test_case"][:42]
            dcol   = _DECISION_COLOUR.get(dec, _RESET)
            print(f"  {i:<4} {label:<44} {score:>5}  {_c(dec, dcol)}")
        print(f"{_BOLD}{DASH}{_RESET}\n")

    if not args.save_db and not args.json_only:
        print(
            f"  {_GREY}[i] MongoDB persistence disabled. "
            f"Run with --save-db to persist results.{_RESET}\n"
        )


if __name__ == "__main__":
    main()
