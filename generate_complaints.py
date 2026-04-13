"""
generate_complaints.py
----------------------
Constructs a synthetic internal complaints series for DII Individual Non-Advised,
working backwards from the real APRA dispute data.

WHY SYNTHETIC?
    APRA publishes dispute data (AFCA-escalated disputes). Internal complaints data
    is held by each insurer and is not publicly available. This script demonstrates
    the methodology an insurer could apply to their own complaints data.

    The synthetic series is constructed to be analytically consistent with the
    real dispute data — it is not arbitrary. The key assumption (complaint-to-dispute
    conversion rate) is documented and can be varied.

CONSTRUCTION METHOD:
    Step 1 — Establish the complaint-to-dispute conversion rate assumption.
             AFCA reports approximately 1 in 5–6 insurance complaints escalate to
             a formal AFCA dispute. We use 18% as our base assumption (midpoint).

    Step 2 — Apply a 2-period (12-month) lead time.
             Internal complaints precede AFCA disputes by approximately 6–12 months,
             reflecting the time for internal IDR (Internal Dispute Resolution) to
             fail before a customer escalates to AFCA.
             We use a 2-period (12-month) lead, consistent with ASIC's RG 271
             requirement for IDR to be completed within 45 days before AFCA escalation
             is possible — and practical observation that most escalations take several
             months after that.

    Step 3 — Add complaint category breakdown.
             Each synthetic complaint is assigned a category, based on known DII
             complaint drivers from AFCA annual reports:
               Claims declined — definition not met:  40%
               Claims delays:                         25%
               Claim amount in dispute:               15%
               Policy terms / coverage unclear:       10%
               Sales conduct / mis-selling:           10%

    Step 4 — Add realistic noise.
             A small random component is added so the series looks like real data
             rather than a mechanical transformation.

CLEAR DISCLOSURE:
    This data is synthetic. It is built to demonstrate the early warning methodology.
    Any insurer can substitute their own complaints data to run the same analysis.

Outputs:
    data/complaints_synthetic.csv   — synthetic internal complaints series, 2017–2025

Usage:
    python3 generate_complaints.py

Requirements:
    pip install pandas numpy
"""

import numpy as np
import pandas as pd
from pathlib import Path

# ── Config ─────────────────────────────────────────────────────────────────────

FOLDER      = Path(__file__).parent
DATA_FOLDER = FOLDER / "data"

RANDOM_SEED = 42

# Key assumption: what % of internal complaints escalate to an AFCA dispute
# Source basis: AFCA Annual Reports suggest ~15–20% of insurance complaints escalate
CONVERSION_RATE = 0.18   # 18% — base assumption

# Lead time: complaints precede disputes by this many half-year periods
LEAD_PERIODS = 2         # 2 periods = 12 months

# Complaint category weights for DII Non-Advised
# Basis: AFCA complaint category data for life insurance, DII-adjusted
COMPLAINT_CATEGORIES = {
    "Claim declined — definition not met":  0.40,
    "Claim delay":                          0.25,
    "Claim amount in dispute":              0.15,
    "Policy terms / coverage unclear":      0.10,
    "Sales conduct / mis-selling":          0.10,
}

# ── Load real dispute rate data ────────────────────────────────────────────────

def load_dispute_trend() -> pd.DataFrame:
    path = DATA_FOLDER / "dispute_trend.csv"
    if not path.exists():
        raise FileNotFoundError(
            "dispute_trend.csv not found. Run load_apra_data.py first."
        )
    df = pd.read_csv(path, parse_dates=['Reporting Date'])
    return df.sort_values('Reporting Date').reset_index(drop=True)


# ── Construct synthetic complaints series ──────────────────────────────────────

def construct_complaints(dispute_trend: pd.DataFrame) -> pd.DataFrame:
    """
    Build a synthetic internal complaints index from the real dispute rate series.

    The complaints series leads the dispute series by LEAD_PERIODS half-years.
    Complaints(t) ≈ Disputes(t + LEAD_PERIODS) / CONVERSION_RATE + noise
    """
    rng = np.random.default_rng(RANDOM_SEED)

    # We need complaints for t = 0 ... n-1
    # For the last LEAD_PERIODS we cannot look forward, so we extrapolate
    dispute_rates = dispute_trend['dispute_rate_per_100k'].values
    dates         = dispute_trend['Reporting Date'].values
    n             = len(dispute_rates)

    # Extend dates backward by LEAD_PERIODS periods (each period = 6 months)
    # Complaints start 12 months before the first dispute observation
    extended_dates = pd.date_range(
        end   = pd.Timestamp(dates[-1]),
        periods = n + LEAD_PERIODS,
        freq  = '6ME'
    )

    # Forward-shifted dispute rates: complaints(i) ∝ dispute_rate(i + LEAD_PERIODS)
    # Pad the end with a simple linear extrapolation of the last 3 points
    last_slope = (dispute_rates[-1] - dispute_rates[-3]) / 2
    extended_rates = np.concatenate([
        dispute_rates,
        [dispute_rates[-1] + last_slope * (k + 1) for k in range(LEAD_PERIODS)]
    ])

    # Complaints = forward dispute rate / conversion rate + noise
    base_complaints = extended_rates / CONVERSION_RATE

    # Add multiplicative noise: ±8% standard deviation
    noise = rng.normal(loc=1.0, scale=0.08, size=len(base_complaints))
    complaints_index = np.maximum(base_complaints * noise, 0)

    # Build the full complaints DataFrame
    complaint_rows = []
    for i, (dt, total) in enumerate(zip(extended_dates, complaints_index)):
        for category, weight in COMPLAINT_CATEGORIES.items():
            # Add category-level noise: ±12%
            cat_noise  = rng.normal(loc=1.0, scale=0.12)
            cat_volume = max(round(total * weight * cat_noise, 1), 0)
            complaint_rows.append({
                'date':     dt,
                'category': category,
                'volume':   cat_volume,
            })

    complaints = pd.DataFrame(complaint_rows)

    # Also produce a total series
    totals = complaints.groupby('date')['volume'].sum().reset_index()
    totals = totals.rename(columns={'volume': 'total_complaints'})
    totals['year_label'] = pd.to_datetime(totals['date']).dt.strftime('%b %Y')

    return complaints, totals


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("Synthetic Complaints Generator — DII Early Warning")
    print("=" * 60)
    print(f"\nAssumptions:")
    print(f"  Complaint-to-dispute conversion rate: {CONVERSION_RATE:.0%}")
    print(f"  Lead time:                            {LEAD_PERIODS} periods ({LEAD_PERIODS * 6} months)")
    print(f"  Complaint categories:                 {len(COMPLAINT_CATEGORIES)}")

    dispute_trend = load_dispute_trend()
    complaints_detail, complaints_totals = construct_complaints(dispute_trend)

    # Save
    complaints_detail.to_csv(DATA_FOLDER / "complaints_synthetic.csv", index=False)
    complaints_totals.to_csv(DATA_FOLDER / "complaints_totals.csv", index=False)

    print(f"\nSynthetic complaints series ({len(complaints_totals)} periods):")
    print(f"  Date range: {complaints_totals['date'].min().strftime('%b %Y')} "
          f"→ {complaints_totals['date'].max().strftime('%b %Y')}")
    print(f"  Volume range: {complaints_totals['total_complaints'].min():.0f} "
          f"– {complaints_totals['total_complaints'].max():.0f} per period")
    print(f"\n{complaints_totals[['year_label','total_complaints']].to_string(index=False)}")

    print(f"\nSaved to {DATA_FOLDER}/")
    print("Next step: streamlit run app.py")


if __name__ == "__main__":
    main()
