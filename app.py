"""
app.py
------
Streamlit dashboard: DII Dispute Early Warning Tool

A cross-functional tool for actuaries, risk managers, operations, and legal teams —
demonstrating how internal complaints data provides a 12-month early warning of
DII dispute deterioration before it becomes an IFRS 17 reserve problem.

Usage:
    streamlit run app.py

Requirements:
    pip install streamlit pandas numpy
"""

import pandas as pd
import numpy as np
import streamlit as st
from pathlib import Path

# ── Page config ────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="DII Dispute Early Warning Tool",
    page_icon="⚠️",
    layout="wide",
)

FOLDER      = Path(__file__).parent
DATA_FOLDER = FOLDER / "data"

# ── Colour palette ─────────────────────────────────────────────────────────────

COLOURS = {
    "DII":        "#C0392B",
    "TPD":        "#2980B9",
    "Trauma":     "#8E44AD",
    "Death":      "#27AE60",
    "Accident":   "#D4AC0D",
    "Other":      "#7F8C8D",
    "complaints": "#E67E22",
    "disputes":   "#C0392B",
    "admitted":   "#27AE60",
    "declined":   "#C0392B",
    "neutral":    "#2C3E50",
    "warning":    "#E67E22",
    "danger":     "#C0392B",
    "safe":       "#27AE60",
}

# ── Data loading ───────────────────────────────────────────────────────────────

@st.cache_data
def load_data():
    dispute_trend    = pd.read_csv(DATA_FOLDER / "dispute_trend.csv",    parse_dates=["Reporting Date"])
    claims_trend     = pd.read_csv(DATA_FOLDER / "claims_trend.csv",     parse_dates=["Reporting Date"])
    by_product       = pd.read_csv(DATA_FOLDER / "dispute_by_product.csv")
    outcomes         = pd.read_csv(DATA_FOLDER / "dispute_outcomes.csv")
    complaints_detail= pd.read_csv(DATA_FOLDER / "complaints_synthetic.csv", parse_dates=["date"])
    complaints_totals= pd.read_csv(DATA_FOLDER / "complaints_totals.csv",    parse_dates=["date"])
    return dispute_trend, claims_trend, by_product, outcomes, complaints_detail, complaints_totals


# ── HTML helpers ───────────────────────────────────────────────────────────────

def metric_card(label, value, sub="", color="#2C3E50"):
    return (
        f"<div style='background:{color};color:white;border-radius:8px;"
        f"padding:14px 16px;text-align:center;margin-bottom:8px;'>"
        f"<div style='font-size:2em;font-weight:bold;'>{value}</div>"
        f"<div style='font-size:0.78em;margin-top:4px;opacity:0.85;'>{sub}</div>"
        f"<div style='font-size:0.75em;margin-top:8px;font-weight:bold;'>{label}</div>"
        f"</div>"
    )


def bar_html(label, value, max_val, color, suffix=""):
    pct = min(value / max_val * 100, 100) if max_val > 0 else 0
    return (
        f"<div style='margin-bottom:10px;'>"
        f"<div style='display:flex;justify-content:space-between;"
        f"font-size:0.85em;margin-bottom:3px;'>"
        f"<span><strong>{label}</strong></span>"
        f"<span style='color:{color};font-weight:bold;'>{value:.0f}{suffix}</span>"
        f"</div>"
        f"<div style='background:#f0f0f0;border-radius:4px;height:14px;'>"
        f"<div style='background:{color};width:{pct:.1f}%;height:14px;border-radius:4px;'></div>"
        f"</div></div>"
    )


def section_header(question, context=""):
    st.markdown(
        f"<div style='background:#f8f9fa;border-left:4px solid #2C3E50;"
        f"padding:14px 18px;border-radius:4px;margin-bottom:20px;'>"
        f"<div style='font-size:1.05em;font-weight:bold;color:#2C3E50;'>{question}</div>"
        + (f"<div style='font-size:0.85em;color:#666;margin-top:6px;'>{context}</div>" if context else "")
        + f"</div>",
        unsafe_allow_html=True
    )


def audience_tag(audience, color):
    return (
        f"<span style='background:{color}22;color:{color};border:1px solid {color}44;"
        f"border-radius:12px;padding:2px 10px;font-size:0.75em;font-weight:bold;"
        f"margin-right:6px;'>{audience}</span>"
    )


def synthetic_badge():
    return (
        "<span style='background:#FFF3CD;color:#856404;border:1px solid #FFEAA7;"
        "border-radius:4px;padding:2px 8px;font-size:0.72em;font-weight:bold;"
        "margin-left:8px;'>CONSTRUCTED DATA</span>"
    )


def real_badge():
    return (
        "<span style='background:#D4EDDA;color:#155724;border:1px solid #C3E6CB;"
        "border-radius:4px;padding:2px 8px;font-size:0.72em;font-weight:bold;"
        "margin-left:8px;'>APRA DATA</span>"
    )


# ── SVG line chart (no matplotlib) ────────────────────────────────────────────

def svg_line_chart(series_dict, title, y_label, width=700, height=280,
                   show_legend=True, annotations=None):
    """
    Render a simple SVG line chart. series_dict = {label: (x_labels, y_values, color)}.
    annotations = list of (x_idx, y_val, text, color)
    """
    pad_l, pad_r, pad_t, pad_b = 60, 20, 30, 50
    chart_w = width - pad_l - pad_r
    chart_h = height - pad_t - pad_b

    all_y = [v for _, vals, _ in series_dict.values() for v in vals if v is not None and not np.isnan(v)]
    if not all_y:
        return ""
    y_min = 0
    y_max = max(all_y) * 1.15

    def x_pos(i, n):
        return pad_l + (i / max(n - 1, 1)) * chart_w

    def y_pos(v):
        return pad_t + chart_h - ((v - y_min) / max(y_max - y_min, 1)) * chart_h

    lines_svg = ""

    # Get x_labels from first series
    first_key = list(series_dict.keys())[0]
    x_labels, _, _ = series_dict[first_key]
    n = len(x_labels)

    # Grid lines
    for tick in [0.25, 0.5, 0.75, 1.0]:
        y_v = y_min + tick * (y_max - y_min)
        yp  = y_pos(y_v)
        lines_svg += (
            f"<line x1='{pad_l}' y1='{yp:.1f}' x2='{pad_l + chart_w}' y2='{yp:.1f}' "
            f"stroke='#e5e5e5' stroke-width='1'/>"
            f"<text x='{pad_l - 6}' y='{yp + 4:.1f}' text-anchor='end' "
            f"font-size='10' fill='#999'>{y_v:.0f}</text>"
        )

    # Series lines
    for label, (x_labs, y_vals, color) in series_dict.items():
        points = []
        for i, v in enumerate(y_vals):
            if v is not None and not np.isnan(v):
                points.append((x_pos(i, len(y_vals)), y_pos(v)))

        if len(points) > 1:
            path_d = " ".join(
                [f"M {points[0][0]:.1f} {points[0][1]:.1f}"] +
                [f"L {px:.1f} {py:.1f}" for px, py in points[1:]]
            )
            lines_svg += (
                f"<path d='{path_d}' fill='none' stroke='{color}' "
                f"stroke-width='2.5' stroke-linejoin='round'/>"
            )
            for px, py in points:
                lines_svg += (
                    f"<circle cx='{px:.1f}' cy='{py:.1f}' r='3' "
                    f"fill='{color}' stroke='white' stroke-width='1'/>"
                )

    # Annotations
    if annotations:
        for x_idx, y_val, text, color in annotations:
            if y_val is not None and not np.isnan(y_val):
                xp = x_pos(x_idx, n)
                yp = y_pos(y_val)
                lines_svg += (
                    f"<circle cx='{xp:.1f}' cy='{yp:.1f}' r='6' "
                    f"fill='{color}' opacity='0.3'/>"
                    f"<text x='{xp:.1f}' y='{yp - 10:.1f}' text-anchor='middle' "
                    f"font-size='9' fill='{color}' font-weight='bold'>{text}</text>"
                )

    # X-axis labels (every 2nd)
    for i, lbl in enumerate(x_labels):
        if i % 2 == 0:
            xp = x_pos(i, n)
            lines_svg += (
                f"<text x='{xp:.1f}' y='{pad_t + chart_h + 18}' "
                f"text-anchor='middle' font-size='9' fill='#666'>{lbl}</text>"
            )

    # Axis lines
    lines_svg += (
        f"<line x1='{pad_l}' y1='{pad_t}' x2='{pad_l}' y2='{pad_t + chart_h}' "
        f"stroke='#ccc' stroke-width='1'/>"
        f"<line x1='{pad_l}' y1='{pad_t + chart_h}' x2='{pad_l + chart_w}' "
        f"y2='{pad_t + chart_h}' stroke='#ccc' stroke-width='1'/>"
    )

    # Y label
    lines_svg += (
        f"<text x='12' y='{pad_t + chart_h // 2}' text-anchor='middle' "
        f"font-size='10' fill='#666' transform='rotate(-90 12 {pad_t + chart_h // 2})'>"
        f"{y_label}</text>"
    )

    # Legend
    legend_svg = ""
    if show_legend:
        lx = pad_l
        ly = height - 12
        for label, (_, _, color) in series_dict.items():
            legend_svg += (
                f"<rect x='{lx}' y='{ly - 8}' width='16' height='4' fill='{color}' rx='2'/>"
                f"<text x='{lx + 20}' y='{ly}' font-size='10' fill='#555'>{label}</text>"
            )
            lx += len(label) * 6.5 + 30

    return (
        f"<svg width='{width}' height='{height}' "
        f"xmlns='http://www.w3.org/2000/svg' "
        f"style='font-family:sans-serif;'>"
        f"<text x='{pad_l + chart_w // 2}' y='16' text-anchor='middle' "
        f"font-size='12' font-weight='bold' fill='#2C3E50'>{title}</text>"
        f"{lines_svg}{legend_svg}"
        f"</svg>"
    )


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    st.title("⚠️ DII Dispute Early Warning Tool")
    st.caption(
        "Income Protection (DII) — Individual Non-Advised channel · "
        "A cross-functional signal tool for actuarial, risk, operations, and legal teams."
    )

    with st.expander("ℹ️ About this tool", expanded=False):
        st.markdown(
            "**The problem this tool addresses:** ASIC's August 2025 review of direct life insurance sales "
            "found that complaints data is siloed — not shared across business units, not connected to "
            "actuarial analysis, not used as a forward-looking signal. By the time dispute rates appear "
            "in APRA statistics, the financial damage is already 12–18 months old.\n\n"
            "**What this tool demonstrates:** Internal complaints data — if monitored and connected to "
            "claims and dispute trends — provides approximately 12 months of early warning before "
            "dispute deterioration becomes visible in published statistics or in IFRS 17 reserves.\n\n"
            "**Who this is for:** This is a cross-functional tool. Each tab is designed to be read "
            "by actuaries, risk managers, operations teams, and legal counsel — without requiring "
            "specialised actuarial knowledge to understand the signal.\n\n"
            "**Data sources:** APRA publishes life insurance claims and disputes statistics as open data. "
            "The dispute rates, claims volumes, and product comparisons shown here are drawn directly "
            "from the official APRA publication. "
            "The internal complaints series does not exist as public data — it is held by each insurer "
            "and is not disclosed. For this tool, it has been synthetically constructed to demonstrate "
            "the methodology. Any insurer can substitute their own complaints data to run the same analysis. "
            "Throughout the tool, APRA data is marked with a green **APRA DATA** badge and constructed "
            "data with a yellow **CONSTRUCTED DATA** badge.\n\n"
            "*Built by Amy Wang (FIAA).*"
        )

    with st.expander("⚠️ Disclaimer", expanded=False):
        st.markdown(
            "This tool uses publicly available APRA statistics and a synthetic complaints series "
            "constructed for illustration purposes. "
            "It does not contain data from any specific insurer. "
            "The IFRS 17 reserve calculations are illustrative only and do not constitute "
            "actuarial advice. All assumptions are documented and clearly disclosed.\n\n"
            "APRA source: *Life Insurance Claims and Disputes Statistics*, June 2025."
        )

    dispute_trend, claims_trend, by_product, outcomes, complaints_detail, complaints_totals = load_data()

    tab1, tab2, tab3, tab4 = st.tabs([
        "📋 The Problem",
        "🔍 The Early Warning Signal",
        "💰 What It Costs If We Miss It",
        "✅ What Good Looks Like",
    ])

    # ── TAB 1: THE PROBLEM ─────────────────────────────────────────────────────
    with tab1:
        section_header(
            "Non-advised / direct-sale DII has a dispute problem — and it has been getting worse for seven years.",
            "Understanding the scale and trajectory of the problem — context for every team in the room."
        )

        # Key metrics
        latest_rate  = dispute_trend['dispute_rate_per_100k'].iloc[-1]
        earliest_rate = dispute_trend['dispute_rate_per_100k'].iloc[0]
        peak_rate    = dispute_trend['dispute_rate_per_100k'].max()
        peak_label   = dispute_trend.loc[dispute_trend['dispute_rate_per_100k'].idxmax(), 'year_label']
        ratio_change = latest_rate / earliest_rate

        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.markdown(metric_card(
                "DII Non-Advised dispute rate today",
                f"{latest_rate:.0f}",
                "disputes per 100,000 lives · Jun 2025",
                COLOURS["neutral"]
            ), unsafe_allow_html=True)
        with m2:
            st.markdown(metric_card(
                "Same rate in 2018",
                f"{earliest_rate:.0f}",
                "disputes per 100,000 lives · Jun 2018",
                COLOURS["neutral"]
            ), unsafe_allow_html=True)
        with m3:
            st.markdown(metric_card(
                "Peak rate observed",
                f"{peak_rate:.0f}",
                f"disputes per 100,000 lives · {peak_label}",
                COLOURS["neutral"]
            ), unsafe_allow_html=True)
        with m4:
            st.markdown(metric_card(
                "Change over 7 years",
                f"+{ratio_change:.1f}×",
                "structural increase, not a blip",
                COLOURS["neutral"]
            ), unsafe_allow_html=True)

        # ── ASIC context — moved to top as the driver of this tool ──────────
        st.markdown(
            "<div style='background:#FFF3CD;border-left:4px solid #E67E22;"
            "padding:14px 16px;border-radius:4px;font-size:0.88em;margin-bottom:20px;'>"
            "<strong>ASIC Dear CEO letter — August 2025:</strong> "
            "ASIC's review of direct life insurance sales found that claims disputes have "
            "<strong>more than doubled since 2018</strong> across all channels. "
            "Companies were found to have limited information sharing about complaints "
            "between internal teams — with insufficient standards for analysing complaint "
            "trends and root causes. "
            "<br><br>"
            "This tool exists because that gap — between the complaints signal and the "
            "actuarial and financial consequence — is exactly what ASIC is asking boards to close."
            "</div>",
            unsafe_allow_html=True
        )

        st.markdown("---")

        col_chart, col_context = st.columns([3, 2])

        with col_chart:
            st.markdown(
                f"**DII dispute rate trend, Individual Non-Advised (2018–2025)** {real_badge()}",
                unsafe_allow_html=True
            )
            labels = dispute_trend['year_label'].tolist()
            rates  = dispute_trend['dispute_rate_per_100k'].tolist()
            peak_idx = dispute_trend['dispute_rate_per_100k'].idxmax()

            chart = svg_line_chart(
                {"Disputes per 100,000 lives": (labels, rates, COLOURS["disputes"])},
                title="",
                y_label="Disputes / 100k lives",
                width=620, height=260,
                show_legend=False,
                annotations=[(peak_idx, peak_rate, f"Peak: {peak_rate:.0f}", COLOURS["danger"])]
            )
            st.markdown(chart, unsafe_allow_html=True)

        with col_context:
            st.markdown("**Why does the direct-sale channel have more disputes?**")
            st.markdown(
                "<div style='font-size:0.83em;color:#888;margin-bottom:10px;font-style:italic;'>"
                "Three reasons from official sources.</div>",
                unsafe_allow_html=True
            )
            st.markdown(
                "<div style='font-size:0.85em;line-height:1.8;'>"
                "<div style='margin-bottom:10px;'><strong>1. No adviser to set expectations.</strong> "
                "In the direct channel, no one checks whether a policy suits the customer before they buy. "
                "When a claim is declined, the customer is often surprised — and disputes. "
                "Claim admittance is 84.6% in direct vs 95.1% in advised. "
                "<em>(APRA Claims and Disputes Statistics)</em></div>"
                "<div style='margin-bottom:10px;'><strong>2. Poor disclosure at point of sale.</strong> "
                "ASIC found direct insurers regularly failed to explain key exclusions and benefit limits clearly. "
                "Customers who didn't understand what they bought dispute when it doesn't pay out. "
                "<em>(ASIC REP 587, 2018; ASIC Dear CEO letter, 2025)</em></div>"
                "<div><strong>3. Sales incentives that prioritised closing the sale.</strong> "
                "Over half of direct insurers had bonus schemes rewarding sales volume over customer suitability. "
                "Unsuitable policies sold under pressure are more likely to end in a dispute. "
                "<em>(ASIC REP 587, 2018)</em></div>"
                "</div>",
                unsafe_allow_html=True
            )

        st.markdown("---")
        st.markdown(
            f"**How does DII compare to other products? (June 2025)** {real_badge()}",
            unsafe_allow_html=True
        )
        st.markdown(
            "<div style='font-size:0.82em;color:#666;margin-bottom:12px;'>"
            "Dispute lodgement ratio = disputes lodged per 100,000 lives insured. "
            "<strong>Individual Non-Advised (direct sales) channel only</strong> — "
            "this is not a comparison of all channels combined. "
            "Rates in the advised channel are materially lower for most products. "
            "Source: APRA Life Insurance Claims and Disputes Statistics, June 2025.</div>",
            unsafe_allow_html=True
        )

        dii_row    = by_product[by_product['product'] == 'DII']
        dii_rate   = float(dii_row['ind_non_advised'].values[0]) if not dii_row.empty else 429
        max_rate   = by_product['ind_non_advised'].dropna().max()

        bars_html = ""
        product_order = ['DII', 'Funeral', 'TPD', 'Trauma', 'Death', 'Accident', 'CCI']
        for prod in product_order:
            row = by_product[by_product['product'] == prod]
            if row.empty:
                continue
            val = row['ind_non_advised'].values[0]
            if pd.isna(val):
                continue
            color = COLOURS["danger"] if prod == "DII" else COLOURS.get(prod, COLOURS["Other"])
            bars_html += bar_html(prod, val, max_rate * 1.05, color)

        st.markdown(
            f"<div style='max-width:500px;'>{bars_html}</div>",
            unsafe_allow_html=True
        )

    # ── TAB 2: THE EARLY WARNING SIGNAL ───────────────────────────────────────
    with tab2:
        section_header(
            "Could we have seen this coming — and how early?",
            "Internal complaints data provides a 12-month lead over published dispute statistics."
        )

        st.markdown(
            f"<div style='margin-bottom:4px;'>"
            + audience_tag("Operations", "#E67E22")
            + audience_tag("Risk", "#8E44AD")
            + audience_tag("Legal", "#2980B9")
            + audience_tag("Actuarial", "#C0392B")
            + "</div>",
            unsafe_allow_html=True
        )

        st.markdown("")

        # Merge complaints and disputes for the chart
        disp = dispute_trend[['Reporting Date', 'dispute_rate_per_100k', 'year_label']].copy()
        comp = complaints_totals[['date', 'total_complaints']].copy()
        comp = comp.rename(columns={'date': 'Reporting Date'})

        merged = disp.merge(comp, on='Reporting Date', how='outer').sort_values('Reporting Date')
        merged['year_label'] = merged['Reporting Date'].dt.strftime('%b %Y')

        # Normalise both series to index (Jun 2018 = 100) for comparison
        disp_base = merged[merged['Reporting Date'] == '2018-06-30']['dispute_rate_per_100k'].values
        comp_base = merged[merged['Reporting Date'] == '2018-06-30']['total_complaints'].values

        if len(disp_base) > 0 and disp_base[0] > 0:
            merged['dispute_index'] = merged['dispute_rate_per_100k'] / disp_base[0] * 100
        else:
            merged['dispute_index'] = merged['dispute_rate_per_100k']

        if len(comp_base) > 0 and comp_base[0] > 0:
            merged['complaint_index'] = merged['total_complaints'] / comp_base[0] * 100
        else:
            merged['complaint_index'] = merged['total_complaints']

        labels = merged['year_label'].tolist()
        d_idx  = merged['dispute_index'].tolist()
        c_idx  = merged['complaint_index'].tolist()

        peak_d_idx = merged['dispute_index'].idxmax() - merged.index[0]
        peak_c_idx = merged['complaint_index'].idxmax() - merged.index[0]

        chart = svg_line_chart(
            {
                f"Complaints (constructed — 12 month lead)": (labels, c_idx, COLOURS["complaints"]),
                f"Disputes (APRA — published data)":         (labels, d_idx, COLOURS["disputes"]),
            },
            title="Complaints vs Disputes — Indexed to Jun 2018 = 100",
            y_label="Index (Jun 2018 = 100)",
            width=700, height=300,
            show_legend=True,
            annotations=[
                (peak_c_idx, c_idx[peak_c_idx] if peak_c_idx < len(c_idx) else None,
                 "Complaint spike", COLOURS["complaints"]),
                (peak_d_idx, d_idx[peak_d_idx] if peak_d_idx < len(d_idx) else None,
                 "Dispute spike", COLOURS["disputes"]),
            ]
        )
        st.markdown(
            f"**Leading indicator chart** {synthetic_badge()} {real_badge()}",
            unsafe_allow_html=True
        )
        st.markdown(chart, unsafe_allow_html=True)

        st.markdown(
            "<div style='background:#FFF8F0;border-left:4px solid #E67E22;"
            "padding:12px 16px;border-radius:4px;font-size:0.85em;margin-top:8px;'>"
            "<strong>Reading this chart:</strong> The orange line (internal complaints) peaks "
            "<strong>approximately 12 months before</strong> the red line (APRA disputes). "
            "The Dec 2020 complaints spike was visible internally — but the corresponding "
            "Dec 2021 dispute spike only appeared in published APRA data a year later. "
            "By that point, the underlying conduct issues were already 12–18 months old."
            "</div>",
            unsafe_allow_html=True
        )

        st.markdown("---")

        col_cat, col_action = st.columns([3, 2])

        with col_cat:
            st.markdown(
                f"**What types of complaints drive DII disputes?** {synthetic_badge()}",
                unsafe_allow_html=True
            )
            st.markdown(
                "<div style='font-size:0.8em;color:#666;margin-bottom:10px;'>"
                "Category weights are constructed assumptions — estimated from AFCA's published "
                "complaint category data for life insurance. AFCA does not publish DII-specific "
                "category splits by channel, so these weights are illustrative. "
                "An insurer with real complaints data would see their own breakdown here.</div>",
                unsafe_allow_html=True
            )
            latest_complaints = complaints_detail[
                complaints_detail['date'] == complaints_detail['date'].max()
            ].copy()
            total_latest = latest_complaints['volume'].sum()
            # Single-hue bars — avoids colour confusion with the team tags in the adjacent column
            bar_color = "#5D6D7E"
            for _, row in latest_complaints.iterrows():
                pct = row['volume'] / total_latest * 100 if total_latest > 0 else 0
                st.markdown(
                    f"<div style='margin-bottom:8px;'>"
                    f"<div style='display:flex;justify-content:space-between;"
                    f"font-size:0.83em;margin-bottom:3px;'>"
                    f"<span>{row['category']}</span>"
                    f"<span style='color:{bar_color};font-weight:bold;'>{pct:.0f}%</span>"
                    f"</div>"
                    f"<div style='background:#f0f0f0;border-radius:4px;height:10px;'>"
                    f"<div style='background:{bar_color};width:{pct:.0f}%;height:10px;border-radius:4px;'></div>"
                    f"</div></div>",
                    unsafe_allow_html=True
                )

        with col_action:
            st.markdown("**Why this matters for each team**")
            audience_items = [
                ("#E67E22", "Operations",
                 "A rising 'Claim declined — definition not met' complaint rate signals that "
                 "front-line staff may be applying policy definitions inconsistently. "
                 "Fix the training before it becomes an AFCA dispute."),
                ("#8E44AD", "Risk",
                 "Rising complaint volume is an emerging risk indicator. "
                 "If it's not on your risk register yet, it should be — "
                 "ASIC's August 2025 letter makes this a board-level issue."),
                ("#2980B9", "Legal",
                 "Each complaint that escalates to AFCA carries legal and reputational cost. "
                 "Complaint trends 12 months out give legal time to prepare, not react."),
                ("#C0392B", "Actuarial",
                 "You are not the owner of complaints data — operations is. "
                 "Your role is to pull it, connect it to dispute trends, and translate the pattern "
                 "into an IFRS 17 LIC implication. That translation is what makes the signal actionable "
                 "for the business. See Tab 3."),
            ]
            for color, team, text in audience_items:
                st.markdown(
                    f"<div style='background:{color}11;border-left:3px solid {color};"
                    f"padding:8px 12px;border-radius:4px;margin-bottom:8px;font-size:0.82em;'>"
                    f"<strong style='color:{color};'>{team}</strong><br>{text}</div>",
                    unsafe_allow_html=True
                )

        st.markdown("---")
        st.markdown("**Illustrative timeline — the journey from complaint to reserve impact**")
        st.markdown(
            "<div style='font-size:0.82em;color:#666;margin-bottom:12px;'>"
            "This timeline is illustrative. The 12-month lead is a documented assumption based on "
            "ASIC's RG 271 IDR requirements and observed AFCA escalation patterns — not a fixed industry rule. "
            "Individual insurers will have different IDR resolution speeds, dispute lodgement patterns, "
            "and reserve review cycles. The key point is directional: complaints lead disputes, "
            "and disputes lead reserve impact. The exact timing will vary by company."
            "</div>",
            unsafe_allow_html=True
        )

        steps = [
            ("📊", "Complaints rise", "Internal data, visible now", "#E67E22"),
            ("⏱️", "+6 months", "IDR process fails, AFCA contacted", "#7F8C8D"),
            ("⚖️", "+12 months", "Dispute lodged, APRA records it", "#C0392B"),
            ("📉", "+18 months", "IFRS 17 LIC impact crystallises", "#2C3E50"),
        ]
        s_cols = st.columns(4)
        for col, (icon, title, sub, color) in zip(s_cols, steps):
            with col:
                st.markdown(
                    f"<div style='text-align:center;padding:12px;background:#f8f9fa;"
                    f"border-radius:8px;border-top:3px solid {color};'>"
                    f"<div style='font-size:1.6em;'>{icon}</div>"
                    f"<div style='font-weight:bold;font-size:0.85em;margin-top:6px;color:{color};'>{title}</div>"
                    f"<div style='font-size:0.78em;color:#666;margin-top:4px;'>{sub}</div>"
                    f"</div>",
                    unsafe_allow_html=True
                )

    # ── TAB 3: WHAT IT COSTS IF WE MISS IT ────────────────────────────────────
    with tab3:
        section_header(
            "What does missing this signal actually cost the business?",
            "The financial and legal consequences — framed for actuaries under IFRS 17."
        )

        st.markdown(
            f"<div style='margin-bottom:8px;'>"
            + audience_tag("Actuarial", "#C0392B")
            + audience_tag("Finance", "#27AE60")
            + audience_tag("Legal", "#2980B9")
            + "</div>",
            unsafe_allow_html=True
        )
        st.markdown("")

        # Dispute outcomes
        st.markdown("### Step 1 — Understand what happens when DII claims are disputed")
        dii_outcomes = outcomes[outcomes['product'] == 'DII'].iloc[0]

        st.markdown(
            "<div style='background:#FFF0F0;border-left:4px solid #C0392B;"
            "padding:14px 16px;border-radius:4px;margin-bottom:16px;font-size:0.88em;'>"
            "<strong>Only 1 in 3 resolved DII disputes results in the original decision being maintained.</strong> "
            "When a DII policyholder escalates to AFCA, the insurer's original decision is upheld "
            "in full in only 33% of cases. In the remaining 67%, the insurer ends up paying "
            "something — either through an outright reversal or a negotiated settlement."
            "</div>",
            unsafe_allow_html=True
        )

        oc1, oc2, oc3 = st.columns(3)
        with oc1:
            pct = dii_outcomes['pct_maintained']
            st.markdown(metric_card(
                "Original decision maintained",
                f"{pct:.0%}",
                "of resolved disputes — insurer wins",
                COLOURS["safe"]
            ), unsafe_allow_html=True)
        with oc2:
            pct = dii_outcomes['pct_reversed']
            st.markdown(metric_card(
                "Original decision reversed",
                f"{pct:.1%}",
                "of resolved disputes — insurer wrong",
                COLOURS["danger"]
            ), unsafe_allow_html=True)
        with oc3:
            pct = dii_outcomes['pct_other_outcome']
            st.markdown(metric_card(
                "Settled / other outcome",
                f"{pct:.0%}",
                "of resolved disputes — insurer pays something",
                COLOURS["warning"]
            ), unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("### Step 2 — The IFRS 17 reserve implication")

        st.markdown(
            "<div style='background:#EBF5FB;border-left:4px solid #2980B9;"
            "padding:14px 16px;border-radius:4px;margin-bottom:16px;font-size:0.88em;line-height:1.7;'>"
            "<strong>Under IFRS 17, the Liability for Incurred Claims (LIC) must reflect "
            "unbiased, probability-weighted estimates of future cash flows.</strong><br><br>"
            "When a DII claim is declined, it does not disappear from the liability picture. "
            "If historical data shows that 67% of disputed declined claims ultimately result "
            "in some payment, then a probability-weighted portion of the declined-claim population "
            "represents an <em>incurred but not yet recognised liability</em>.<br><br>"
            "An actuary who models the LIC using only admitted claims — without probability-weighting "
            "the disputed population — is <strong>overstating the CSM and understating the LIC</strong>. "
            "The error is silent until AFCA decisions start coming in, at which point it is "
            "too late to avoid the reserve strengthening."
            "</div>",
            unsafe_allow_html=True
        )

        st.markdown("### Step 3 — Quantify the impact")
        st.markdown(
            "_Adjust the sliders to reflect your portfolio assumptions. "
            "The calculator shows the probability-weighted additional liability "
            "per 1,000 DII claims received._"
        )

        st.markdown(
            "<div style='background:#F8F9FA;border:1px solid #dee2e6;border-radius:6px;"
            "padding:14px 16px;margin-bottom:16px;font-size:0.83em;line-height:1.7;'>"
            "<strong>Calculator assumptions and data sources</strong><br>"
            "<table style='width:100%;border-collapse:collapse;margin-top:8px;'>"
            "<tr><td style='width:40%;color:#555;padding:2px 0;'><strong>Decline rate default (12%)</strong></td>"
            "<td style='color:#444;'>APRA claims data, DII Non-Advised, Jun 2025: ~11.5% of claims received were declined. "
            "Rounded to 12% as base. <span style='color:#155724;font-weight:bold;'>APRA DATA</span></td></tr>"
            "<tr><td style='color:#555;padding:2px 0;'><strong>Dispute rate default (40%)</strong></td>"
            "<td style='color:#444;'>Estimated from APRA dispute volumes relative to decline volumes. "
            "Not directly published — this is a derived assumption. <span style='color:#856404;font-weight:bold;'>CONSTRUCTED</span></td></tr>"
            "<tr><td style='color:#555;padding:2px 0;'><strong>Payment probability default (67%)</strong></td>"
            "<td style='color:#444;'>From APRA outcomes data, Jun 2025: 33.2% of resolved DII disputes resulted in "
            "original decision maintained — so 66.8% resulted in some payment (reversal or settlement). "
            "<span style='color:#155724;font-weight:bold;'>APRA DATA</span></td></tr>"
            "<tr><td style='color:#555;padding:2px 0;'><strong>Average payment ($25,000)</strong></td>"
            "<td style='color:#444;'>Illustrative only. AFCA does not publish average payment amounts by product. "
            "Intended to represent a partial benefit payment, not a full claim. "
            "<span style='color:#856404;font-weight:bold;'>ILLUSTRATIVE</span></td></tr>"
            "<tr><td style='color:#555;padding:2px 0;'><strong>Formula</strong></td>"
            "<td style='color:#444;'>LIC = claims received × decline rate × dispute rate × payment probability × avg payment</td></tr>"
            "</table></div>",
            unsafe_allow_html=True
        )

        calc_col, result_col = st.columns([2, 1])

        with calc_col:
            decline_rate    = st.slider(
                "Decline rate (% of claims received that are declined)",
                min_value=5, max_value=25, value=12, step=1,
                help="DII Non-Advised decline rate at Jun 2025: ~11.5%"
            )
            dispute_pct     = st.slider(
                "Dispute rate (% of declined claims that are disputed)",
                min_value=10, max_value=80, value=40, step=5,
                help="Estimated based on APRA dispute volumes relative to decline volumes"
            )
            payment_prob    = st.slider(
                "Payment probability (% of disputed claims that result in some payment)",
                min_value=30, max_value=90, value=67, step=1,
                help="From APRA data: 33.2% of resolved DII disputes maintained — so 66.8% result in payment"
            )
            avg_payment     = st.slider(
                "Average payment per resolved dispute ($000s)",
                min_value=5, max_value=100, value=25, step=5,
                help="Illustrative — based on general DII benefit levels in the direct channel"
            )

        with result_col:
            claims_received    = 1000
            claims_declined    = claims_received * decline_rate / 100
            claims_disputed    = claims_declined * dispute_pct / 100
            expected_payments  = claims_disputed * payment_prob / 100
            total_liability    = expected_payments * avg_payment * 1000

            st.markdown(
                f"<div style='background:#2C3E50;color:white;border-radius:8px;"
                f"padding:20px;text-align:center;'>"
                f"<div style='font-size:0.8em;opacity:0.8;'>Per 1,000 claims received</div>"
                f"<div style='font-size:0.9em;margin-top:12px;'>Claims declined</div>"
                f"<div style='font-size:1.6em;font-weight:bold;'>{claims_declined:.0f}</div>"
                f"<div style='font-size:0.9em;margin-top:8px;'>Likely disputed</div>"
                f"<div style='font-size:1.6em;font-weight:bold;'>{claims_disputed:.0f}</div>"
                f"<div style='font-size:0.9em;margin-top:8px;'>Expected to result in payment</div>"
                f"<div style='font-size:1.6em;font-weight:bold;'>{expected_payments:.0f}</div>"
                f"<div style='background:#C0392B;border-radius:6px;margin-top:14px;padding:10px;'>"
                f"<div style='font-size:0.8em;opacity:0.9;'>Probability-weighted additional LIC</div>"
                f"<div style='font-size:2em;font-weight:bold;'>${total_liability/1e6:.2f}M</div>"
                f"</div></div>",
                unsafe_allow_html=True
            )

        st.markdown("---")
        st.markdown("### The cost of being reactive vs proactive")

        cost_cols = st.columns(3)
        cost_items = [
            ("#C0392B", "Reserve strengthening",
             "When disputed claims resolve adversely, the LIC must be strengthened. "
             "Done reactively — after AFCA decisions — this creates volatile earnings and "
             "capital impacts under IFRS 17. Done proactively via complaint monitoring, "
             "the strengthening is gradual and manageable."),
            ("#E67E22", "AFCA process cost",
             "Each AFCA dispute carries direct cost: case management, legal review, "
             "and AFCA levy per complaint. For a large DII direct portfolio, "
             "this is a material operating cost line — and it scales with dispute volume."),
            ("#2980B9", "Regulatory and reputational risk",
             "ASIC has explicitly stated that the steps taken in responding to their "
             "August 2025 observations will inform enforcement action. "
             "A documented early warning framework is evidence of governance — "
             "its absence is evidence of the opposite."),
        ]
        for col, (color, title, text) in zip(cost_cols, cost_items):
            with col:
                st.markdown(
                    f"<div style='background:{color}11;border-top:3px solid {color};"
                    f"padding:14px;border-radius:4px;height:200px;'>"
                    f"<div style='font-weight:bold;color:{color};font-size:0.9em;"
                    f"margin-bottom:8px;'>{title}</div>"
                    f"<div style='font-size:0.82em;color:#444;line-height:1.6;'>{text}</div>"
                    f"</div>",
                    unsafe_allow_html=True
                )

    # ── TAB 4: WHAT GOOD LOOKS LIKE ────────────────────────────────────────────
    with tab4:
        section_header(
            "What would we change if we ran this analysis every quarter?",
            "A connected early warning framework — what each team owns, and what the actuary connects."
        )

        st.markdown(
            f"<div style='margin-bottom:8px;'>"
            + audience_tag("Leadership", "#2C3E50")
            + audience_tag("Risk", "#8E44AD")
            + audience_tag("Operations", "#2980B9")
            + audience_tag("Actuarial", "#C0392B")
            + "</div>",
            unsafe_allow_html=True
        )
        st.markdown("")

        st.markdown("### The connected monitoring framework")
        st.markdown(
            "ASIC's observation is that data exists but is not shared or connected. "
            "Below is what a better practice framework looks like — and what role each team plays."
        )

        framework_items = [
            ("#E67E22", "01", "Collect", "Complaints Team / Operations",
             "Every internal complaint is logged with: date, product, channel, complaint category, "
             "and resolution outcome. Not just volume — categorised, so trends by type are visible. "
             "The ASIC standard (RG 271) requires firms to enable staff to escalate systemic issues. "
             "This only works if the data exists in usable form."),
            ("#F39C12", "02", "Connect", "Actuarial",
             "Monthly: the actuary receives complaints data from operations and overlays it on "
             "the APRA dispute trend. The 12-month lead relationship is monitored. "
             "When the complaint trend diverges upward from the historical pattern, a flag is raised. "
             "This is the connection ASIC found missing — complaints data not reaching actuarial."),
            ("#C0392B", "03", "Monitor", "Risk / Board",
             "A quarterly dashboard — like this one — is reviewed by the Risk Committee. "
             "Three traffic lights: complaint trend (leading), dispute rate (current), "
             "LIC adequacy (lagging). All three in the same view, owned by a named person. "
             "ASIC expects boards to be sighted on this. The actuary's role is to make it readable "
             "for the board, not just technically correct."),
            ("#2C3E50", "04", "Act", "Cross-functional",
             "When a signal turns amber: operations reviews claim decline rationale and staff training. "
             "When a signal turns red: legal is notified of AFCA exposure, actuarial strengthens the "
             "LIC probability weight, product team reviews whether the policy definition is causing "
             "systematic mismatches at claim time. Action is predefined — not improvised in a crisis."),
        ]

        for color, num, step, owner, text in framework_items:
            st.markdown(
                f"<div style='display:flex;gap:16px;margin-bottom:14px;"
                f"background:#f8f9fa;border-radius:8px;padding:14px;'>"
                f"<div style='min-width:48px;height:48px;background:{color};"
                f"border-radius:50%;display:flex;align-items:center;justify-content:center;"
                f"color:white;font-weight:bold;font-size:1.1em;'>{num}</div>"
                f"<div style='flex:1;'>"
                f"<div style='font-weight:bold;font-size:0.95em;margin-bottom:2px;'>"
                f"{step} <span style='color:{color};'>— {owner}</span></div>"
                f"<div style='font-size:0.83em;color:#444;line-height:1.6;'>{text}</div>"
                f"</div></div>",
                unsafe_allow_html=True
            )

        st.markdown("---")
        st.markdown("### Quarterly signal dashboard — illustrative current status")
        st.markdown(
            "<div style='background:#EBF5FB;border-left:4px solid #2980B9;"
            "padding:14px 16px;border-radius:4px;margin-bottom:14px;font-size:0.85em;line-height:1.7;'>"
            "<strong>What this shows:</strong> Rather than presenting a detailed technical report to "
            "the board each quarter, the actuary condenses the three monitoring signals into a single "
            "one-page view — each signal at a different point in time, each owned by a named person.<br><br>"
            "<strong>Leading signal (complaints):</strong> What the data is telling us now, "
            "approximately 12 months before it appears in published statistics.<br>"
            "<strong>Current signal (disputes):</strong> What has already arrived — the published "
            "APRA dispute rate for the most recent half-year.<br>"
            "<strong>Lagging signal (LIC):</strong> Whether the IFRS 17 reserve has been updated "
            "to reflect what we now know. This is the actuary's owned output.<br><br>"
            "Signal status below is calculated from the actual data in this tool — not illustrative values. "
            "Thresholds: amber = &gt;10% increase in complaints or &gt;5% change in dispute rate; "
            "LIC held at amber while dispute rate remains elevated above 7-year average.</div>",
            unsafe_allow_html=True
        )

        latest_rate = dispute_trend['dispute_rate_per_100k'].iloc[-1]
        prev_rate   = dispute_trend['dispute_rate_per_100k'].iloc[-3]
        rate_change = (latest_rate - prev_rate) / prev_rate

        latest_comp  = complaints_totals['total_complaints'].iloc[-1]
        prev_comp    = complaints_totals['total_complaints'].iloc[-3]
        comp_change  = (latest_comp - prev_comp) / prev_comp

        def traffic_light(status, label, value, detail, owner):
            colors = {"green": "#27AE60", "amber": "#E67E22", "red": "#C0392B"}
            icons  = {"green": "✓", "amber": "⚠", "red": "✗"}
            c = colors[status]
            return (
                f"<div style='border:1px solid {c}33;border-radius:8px;"
                f"padding:14px;background:{c}08;'>"
                f"<div style='display:flex;align-items:center;gap:10px;margin-bottom:8px;'>"
                f"<div style='width:32px;height:32px;background:{c};border-radius:50%;"
                f"display:flex;align-items:center;justify-content:center;"
                f"color:white;font-weight:bold;font-size:1.1em;'>{icons[status]}</div>"
                f"<div style='font-weight:bold;font-size:0.9em;'>{label}</div>"
                f"</div>"
                f"<div style='font-size:1.4em;font-weight:bold;color:{c};margin-bottom:4px;'>"
                f"{value}</div>"
                f"<div style='font-size:0.78em;color:#555;margin-bottom:6px;'>{detail}</div>"
                f"<div style='font-size:0.75em;color:#888;'><strong>Owner:</strong> {owner}</div>"
                f"</div>"
            )

        comp_status = "amber" if comp_change > 0.1 else "green"
        disp_status = "amber" if rate_change > 0.05 else "green" if rate_change < -0.05 else "amber"
        lic_status  = "amber"

        tl1, tl2, tl3 = st.columns(3)
        with tl1:
            st.markdown(
                traffic_light(
                    comp_status,
                    "Complaint Trend (Leading — 12 months)",
                    f"{latest_comp:,.0f} / period",
                    f"{'↑' if comp_change > 0 else '↓'} {abs(comp_change):.0%} vs 12 months ago. "
                    f"'Claim declined' category rising.",
                    "Operations / Complaints Manager"
                ),
                unsafe_allow_html=True
            )
        with tl2:
            st.markdown(
                traffic_light(
                    disp_status,
                    "Dispute Rate (Current — APRA)",
                    f"{latest_rate:.0f} / 100k lives",
                    f"{'↑' if rate_change > 0 else '↓'} {abs(rate_change):.0%} vs 12 months ago. "
                    f"Above 7-year average of 285.",
                    "Actuarial / Risk"
                ),
                unsafe_allow_html=True
            )
        with tl3:
            st.markdown(
                traffic_light(
                    lic_status,
                    "LIC Adequacy (Lagging — IFRS 17)",
                    "Probability weight: 67%",
                    "Disputed-claim LIC probability weight last reviewed Q2 2025. "
                    "Recommend quarterly review while dispute rate elevated.",
                    "Appointed Actuary"
                ),
                unsafe_allow_html=True
            )

        st.markdown("")
        st.info(
            "**The actuary's role in this framework is connective, not just technical.** "
            "The complaint data comes from operations. The dispute data comes from APRA. "
            "The IFRS 17 implication is actuarial. Connecting all three — and presenting "
            "it in a form the Risk Committee can act on — is the senior actuary's contribution. "
            "That is what this tool demonstrates."
        )


if __name__ == "__main__":
    main()
