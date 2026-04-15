# Risk Scoring Engine — Video-Based Loan Origination System

A **production-grade, modular risk scoring engine** that ingests bureau data,
STT-derived inputs, fraud signals, and policy rules to produce an explainable
`0–1000` risk score, risk band, decision, and natural-language explanation.

---

## Project Structure

```
risc_score/
├── config.py              # All thresholds, weights, MongoDB settings
├── models.py              # Pydantic input/output schemas
├── feature_engineering.py # EMI calc, FOIR, normalisation (0–1000)
├── rules_engine.py        # Hard-decline policy checks
├── risk_engine.py         # Core orchestrator pipeline
├── database.py            # MongoDB audit persistence layer
├── utils.py               # EMI formula, scalers, NL explanation gen
├── main.py                # CLI runner with 6 built-in test cases
└── requirements.txt
```

---

## Quick Start

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Run all test cases
```bash
python main.py
```

### 3. Run with MongoDB persistence
```bash
# Requires MongoDB running on localhost:27017
python main.py --save-db
```

### 4. Raw JSON output (for downstream integration)
```bash
python main.py --json-only
```

---

## Scoring Architecture

### Pipeline (per application)
```
Input JSON
    │
    ▼
[1] Pydantic Validation       ← models.py
    │
    ▼
[2] Feature Engineering       ← feature_engineering.py
    │  · Compute proposed EMI (reducing balance formula)
    │  · Derive FOIR
    │  · Normalise 7 features → 0–1000 each
    │
    ▼
[3] Hard-Decline Rules        ← rules_engine.py
    │  · FOIR > 65%  → DECLINE
    │  · NPA present → DECLINE
    │  · CIBIL < 650 → DECLINE
    │  · DPD 90+ ≥ 3 → DECLINE
    │  · Income match < 70% → DECLINE
    │
    ▼
[4] Weighted Risk Score       ← risk_engine.py
    │
    ▼
[5] Risk Band + Decision
    │
    ▼
[6] Fraud Flag Detection
    │
    ▼
[7] Reason Code Generation
    │
    ▼
[8] NL Explanation
    │
    ▼
[9] MongoDB Audit Persist     ← database.py
    │
    ▼
Output JSON
```

### Scoring Weights

| Feature              | Weight |
|----------------------|--------|
| CIBIL Score          | 25%    |
| FOIR                 | 20%    |
| DPD 90+              | 15%    |
| Credit Utilisation   | 10%    |
| Enquiry Count (6M)   | 10%    |
| Employment Tenure    | 10%    |
| Income Verification  | 10%    |

### Risk Bands

| Score     | Band      | Decision        |
|-----------|-----------|-----------------|
| 700–1000  | LOW       | APPROVE         |
| 550–699   | MEDIUM    | REDUCE (offer)  |
| 400–549   | HIGH      | REVIEW (manual) |
| < 400     | VERY_HIGH | DECLINE         |

---

## Sample Output

```json
{
  "risk_score": 859,
  "risk_band": "LOW",
  "decision": "APPROVE",
  "foir": 0.1483,
  "flags": ["NONE"],
  "reason_codes": [
    "GOOD_CIBIL",
    "LOW_FOIR",
    "NO_DPD",
    "LOW_CREDIT_UTILIZATION",
    "STABLE_EMPLOYMENT",
    "INCOME_VERIFIED",
    "LOW_ENQUIRIES",
    "LONG_CREDIT_HISTORY"
  ],
  "top_factors": ["cibil", "foir", "dpd"],
  "llm_explanation": "This applicant presents a low risk profile. The applicant
    demonstrates strong credit score, manageable debt obligations, clean repayment
    history... Based on the scoring analysis, we recommend full loan approval."
}
```

---

## Test Case Summary (Built-in Scenarios)

| # | Scenario                         | Score | Decision |
|---|----------------------------------|-------|----------|
| 1 | Ideal Applicant                  | 859   | APPROVE  |
| 2 | Spec Sample (Moderate FOIR)      | 665   | REDUCE   |
| 3 | High FOIR                        | 0     | DECLINE  |
| 4 | NPA Present                      | 0     | DECLINE  |
| 5 | Fraud Signals + Borderline Score | 563   | REDUCE * |
| 6 | Young Applicant Low History      | 619   | REDUCE   |

> \* Fraud flags active: `FRAUD_GEO_MISMATCH`, `FRAUD_MULTIPLE_APPLICATIONS`, `FRAUD_HIGH_ENQUIRY_COUNT`

---

## MongoDB Schema

Audit records are stored in `risk_scoring_db.loan_applications`:

```json
{
  "application_id": "APP-20260415191828-1FB5EB3D",
  "timestamp": "2026-04-15T19:18:28+00:00",
  "input_data": { ... },
  "computed_features": { ... },
  "hard_decline_result": { ... },
  "output": { ... }
}
```

Indexes: `application_id` (unique), `timestamp`.

---

## Extending the Engine

| Task                          | File to modify          |
|-------------------------------|-------------------------|
| Add a new hard-decline rule   | `rules_engine.py`       |
| Adjust score weights          | `config.py`             |
| Plug in a real bureau API     | `risk_engine.py` step 1 |
| Add a new feature/normaliser  | `feature_engineering.py`|
| Tune risk band thresholds     | `config.py`             |
| Add new reason codes          | `config.py` + `risk_engine.py` |

---

## Dependencies

- **pydantic ≥ 2.0** — input validation and schema enforcement  
- **pymongo ≥ 4.6**  — MongoDB audit persistence (optional; degrades gracefully)
