# DII Dispute Early Warning Tool

A Streamlit dashboard that monitors DII (Disability Income Insurance) dispute trends using APRA data, flags early warning signals, and helps insurers identify portfolio-level dispute risk before complaints reach AFCA.

---

## What It Does

**4 tabs:**

| Tab | Purpose |
|-----|---------|
| Industry Overview | APRA dispute trends, dispute rate per 100k policies, 7-year average benchmarks |
| Early Warning Signals | Complaint and dispute index tracking, peak identification, lead/lag analysis |
| Portfolio Risk Assessment | Traffic light system for dispute rate, resolution outcomes, and complaint volume |
| Governance & Action | Recommended monitoring cadence, escalation triggers, and governance framework |

---

## Data Sources

- **APRA Life Insurance Disputes Statistics** — industry-level dispute data, June 2018 to June 2025
- **Synthetic complaint data** — constructed to illustrate portfolio monitoring methodology

APRA data is sourced from publicly available statistics. Synthetic data is clearly labelled throughout the dashboard.

---

## Regulatory Context

ASIC's REP 587 (2019) identified DII claims handling as a systemic issue. ASIC's Dear CEO letter (August 2025) confirmed the issue persists, with insurers expected to demonstrate active dispute risk management. This tool provides the monitoring framework to do that.

---

## Technical Stack

- **Python / Streamlit** — dashboard framework
- **pandas** — APRA data processing
- **Hand-built HTML charts** — bar and trend visualisations

---

## Project Structure

```
ComplaintsTool/
├── app.py                    # Main dashboard
├── load_apra_data.py         # APRA data loading and processing
├── generate_complaints.py    # Synthetic complaint data generation
├── requirements.txt
└── data/                     # Processed data files
```

---

## Running Locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

Opens at `http://localhost:8501`.

---

## Disclaimer

This dashboard is for demonstration purposes only. APRA data reflects industry aggregates — it is not company-specific. Synthetic data is constructed for illustration and does not represent any real insurer's portfolio. Traffic light thresholds are illustrative and should be calibrated to a specific portfolio before use.

---

*Built by Amy Wang, FIAA.*
