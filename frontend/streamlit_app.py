"""
DataPilot — Agentic AI Data Analysis Tool
=========================================
Streamlit Frontend Application (Mission 1 MVP)

Features:
  - File upload (CSV / Excel) with instant SHA-256 versioning
  - Composite & 4-Dimension Data Quality Scorecard
  - Full Evidence Traceability: click to view exact tool & math behind any number
  - Descriptive Statistics & Pearson Correlation Heatmap
  - 3 Independent Anomaly Detection Engine (IQR, Z-Score, Isolation Forest)
  - Interactive Plotly visualizations with red-flagged anomaly points
  - Downloadable JSON audit bundle
"""

import json
from typing import Any
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

from app.data.ingestion import load_file, IngestionError
from app.data.quality import score_quality
from app.analytics.statistics import compute_descriptive_stats
from app.analytics.correlations import compute_correlation_matrix
from app.anomaly.iqr import detect_iqr
from app.anomaly.zscore import detect_zscore
from app.anomaly.isolation_forest import detect_isolation_forest
from app.visualization.chart_selector import select_charts, render_chart
from app.models.pydantic import QualityReport, AnomalySummary, EvidenceObject

# Page Configuration
st.set_page_config(
    page_title="DataPilot — Agentic Data Profiler & Anomaly Detector",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling (Dark Glassmorphism Theme)
st.markdown(
    """
    <style>
    /* Global styles */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    /* Header styling */
    .main-header {
        background: linear-gradient(135deg, #1e1b4b 0%, #312e81 50%, #4338ca 100%);
        padding: 1.5rem 2rem;
        border-radius: 12px;
        color: white;
        margin-bottom: 2rem;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
    }
    .main-header h1 {
        margin: 0;
        font-size: 2.2rem;
        font-weight: 700;
        color: #f8fafc;
    }
    .main-header p {
        margin: 0.4rem 0 0 0;
        color: #c7d2fe;
        font-size: 1.05rem;
    }

    /* Card container */
    .glass-card {
        background: rgba(30, 41, 59, 0.7);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 1.25rem 1.5rem;
        margin-bottom: 1.25rem;
        backdrop-filter: blur(10px);
    }

    /* Score badges */
    .score-badge-high {
        color: #10b981;
        font-weight: 700;
        font-size: 2.5rem;
    }
    .score-badge-medium {
        color: #f59e0b;
        font-weight: 700;
        font-size: 2.5rem;
    }
    .score-badge-low {
        color: #ef4444;
        font-weight: 700;
        font-size: 2.5rem;
    }

    /* Metric pill */
    .metric-pill {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 8px;
        padding: 0.75rem 1rem;
        text-align: center;
        border: 1px solid rgba(255, 255, 255, 0.05);
    }
    .metric-pill-val {
        font-size: 1.4rem;
        font-weight: 600;
        color: #60a5fa;
    }
    .metric-pill-lbl {
        font-size: 0.85rem;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Header Banner
st.markdown(
    """
    <div class="main-header">
        <h1>🚀 DataPilot</h1>
        <p>Deterministic Data Quality Profiler, Statistical Engine & Tri-Method Anomaly Detector</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# Sidebar configuration & upload
with st.sidebar:
    st.header("📥 Data Source")
    uploaded_file = st.file_uploader(
        "Upload a dataset (CSV, XLSX, XLS)",
        type=["csv", "xlsx", "xls"],
        help="Maximum size: 200MB. Supported formats: CSV, Excel",
    )
    
    st.divider()
    st.markdown("### ⚙️ Engine Parameters")
    z_thresh = st.slider("Z-Score Threshold", 1.5, 5.0, 3.0, 0.1)
    iqr_mult = st.slider("IQR Multiplier (Tukey Fence)", 1.0, 3.0, 1.5, 0.1)
    st.caption("🔒 All numbers displayed originate from deterministic Python/ML tool calls backed by verifiable Evidence Objects.")

if uploaded_file is None:
    st.info("👈 Please upload a CSV or Excel file from the sidebar to start profiling.")
    
    st.markdown("### 💡 Sample Datasets")
    st.write("You can test DataPilot using the pre-generated synthetic datasets in `scripts/sample_data/`:")
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("**Clean Dataset (`clean_data.csv`)**")
        st.caption("500 rows, 5 numeric columns, zero nulls/duplicates, high quality score (~98).")
    with col_b:
        st.markdown("**Messy Dataset (`messy_data.csv`)**")
        st.caption("500 rows with 12% nulls, duplicate rows, type mismatches, and 5 known injected outliers.")
    st.stop()

# Execution Pipeline
try:
    with st.spinner("Ingesting and parsing file..."):
        file_bytes = uploaded_file.getvalue()
        df, ingestion_res = load_file(file_bytes, uploaded_file.name)
except IngestionError as err:
    st.error(f"❌ Ingestion Error: {err}")
    st.stop()
except Exception as err:
    st.error(f"❌ Unexpected Error during ingestion: {err}")
    st.stop()

# Step 2: Quality Scoring
with st.spinner("Scoring Data Quality..."):
    quality_rep: QualityReport = score_quality(df, ingestion_res.dataset_version, ingestion_res.filename)

# Step 3: Statistical Profiling
with st.spinner("Computing Descriptive Statistics & Correlations..."):
    stats_res = compute_descriptive_stats(df, ingestion_res.dataset_version)
    corr_res = compute_correlation_matrix(df, ingestion_res.dataset_version)

# Step 4: Anomaly Detection
with st.spinner("Running Anomaly Detectors (IQR, Z-Score, Isolation Forest)..."):
    iqr_res = detect_iqr(df, ingestion_res.dataset_version)
    zscore_res = detect_zscore(df, ingestion_res.dataset_version)
    iforest_res = detect_isolation_forest(df, ingestion_res.dataset_version)
    anomaly_summaries = [iqr_res, zscore_res, iforest_res]

# Step 5: Visualizations Selection
chart_specs = select_charts(df, quality_rep, anomaly_summaries, corr_res, stats_res)

# Layout Tabs
tab_overview, tab_quality, tab_stats, tab_anomalies, tab_charts, tab_evidence = st.tabs([
    "📊 Dataset Overview",
    "🛡️ Data Quality Score",
    "📈 Descriptive Stats",
    "🔍 Anomaly Detection",
    "📉 Visualizations",
    "📜 Evidence Audit Log",
])

# -----------------------------------------------------------------------------
# TAB 1: OVERVIEW
# -----------------------------------------------------------------------------
with tab_overview:
    st.subheader("📋 Dataset Overview")
    
    m1, m2, m3, m4, m5 = st.columns(5)
    with m1:
        st.markdown(f"<div class='metric-pill'><div class='metric-pill-val'>{ingestion_res.n_rows:,}</div><div class='metric-pill-lbl'>Rows</div></div>", unsafe_allow_html=True)
    with m2:
        st.markdown(f"<div class='metric-pill'><div class='metric-pill-val'>{ingestion_res.n_cols}</div><div class='metric-pill-lbl'>Columns</div></div>", unsafe_allow_html=True)
    with m3:
        size_mb = ingestion_res.file_size_bytes / (1024 * 1024)
        st.markdown(f"<div class='metric-pill'><div class='metric-pill-val'>{size_mb:.2f} MB</div><div class='metric-pill-lbl'>File Size</div></div>", unsafe_allow_html=True)
    with m4:
        st.markdown(f"<div class='metric-pill'><div class='metric-pill-val'>{quality_rep.composite_score:.1f}/100</div><div class='metric-pill-lbl'>Quality Score</div></div>", unsafe_allow_html=True)
    with m5:
        total_anom = sum(s.n_flagged for s in anomaly_summaries)
        st.markdown(f"<div class='metric-pill'><div class='metric-pill-val'>{total_anom}</div><div class='metric-pill-lbl'>Anomalies Flagged</div></div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(f"**Dataset SHA-256 Version:** `{ingestion_res.dataset_version}`")
    
    st.markdown("#### Preview (First 10 Rows)")
    st.dataframe(df.head(10), use_container_width=True)

    st.markdown("#### Column Schema & Types")
    col_types_df = pd.DataFrame([
        {
            "Column Name": prof.column_name,
            "Detected Data Type": prof.dtype,
            "Missing Count": prof.n_missing,
            "Missing %": f"{prof.pct_missing:.1f}%",
            "Unique Count": prof.n_unique,
            "Sample Values": ", ".join(prof.sample_values[:3]),
        }
        for prof in quality_rep.column_profiles
    ])
    st.dataframe(col_types_df, use_container_width=True)

# -----------------------------------------------------------------------------
# TAB 2: DATA QUALITY SCORECARD
# -----------------------------------------------------------------------------
with tab_quality:
    st.subheader("🛡️ Data Quality Scorecard")
    
    score = quality_rep.composite_score
    badge_cls = "score-badge-high" if score >= 80 else ("score-badge-medium" if score >= 60 else "score-badge-low")
    
    col_score, col_summary = st.columns([1, 2])
    with col_score:
        st.markdown(
            f"""
            <div style="text-align: center; padding: 1.5rem; background: rgba(30, 41, 59, 0.8); border-radius: 12px; border: 1px solid rgba(255,255,255,0.1);">
                <div style="color: #94a3b8; font-size: 0.9rem; text-transform: uppercase;">Composite Data Quality Score</div>
                <div class="{badge_cls}">{score:.1f}<span style="font-size: 1.2rem; color: #94a3b8;">/100</span></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col_summary:
        st.markdown("#### Quality Breakdown by Dimension")
        st.write("DataPilot scores quality deterministically across four key dimensions:")

    dim_cols = st.columns(4)
    for idx, dim in enumerate(quality_rep.dimensions):
        with dim_cols[idx]:
            d_score = dim.score
            d_cls = "#10b981" if d_score >= 80 else ("#f59e0b" if d_score >= 60 else "#ef4444")
            st.markdown(
                f"""
                <div style="background: rgba(30, 41, 59, 0.6); padding: 1rem; border-radius: 8px; border-left: 4px solid {d_cls}; margin-bottom: 1rem;">
                    <div style="font-weight: 600; text-transform: capitalize;">{dim.name}</div>
                    <div style="font-size: 1.6rem; font-weight: 700; color: {d_cls};">{d_score:.1f}%</div>
                    <div style="font-size: 0.8rem; color: #cbd5e1; margin-top: 0.4rem;">{dim.reason}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            with st.expander(f"🔍 Evidence for {dim.name}"):
                st.code(dim.evidence.calculation, language="text")
                st.json(dim.evidence.model_dump())

# -----------------------------------------------------------------------------
# TAB 3: DESCRIPTIVE STATISTICS
# -----------------------------------------------------------------------------
with tab_stats:
    st.subheader("📈 Statistical Profile")
    
    if not stats_res:
        st.warning("No numeric columns found in dataset.")
    else:
        stats_data = []
        for s in stats_res:
            stats_data.append({
                "Column": s.column,
                "Valid Count": s.n_valid,
                "Mean": s.mean,
                "Std Dev": s.std,
                "Min": s.min_val,
                "Q1 (25%)": s.q1,
                "Median": s.median,
                "Q3 (75%)": s.q3,
                "Max": s.max_val,
                "Skewness": s.skewness,
                "Kurtosis": s.kurtosis,
            })
        st.dataframe(pd.DataFrame(stats_data), use_container_width=True)

        st.markdown("#### 🔍 Evidence Traceability for Column Stats")
        selected_stat_col = st.selectbox("Select column to view stat calculation details:", [s.column for s in stats_res])
        selected_stat = next(s for s in stats_res if s.column == selected_stat_col)
        st.info(f"**Calculation Formula:** {selected_stat.evidence.calculation}")
        st.json(selected_stat.evidence.model_dump())

        if corr_res:
            st.markdown("#### 🔗 Pearson Correlation Matrix")
            corr_df_list = [
                {"Column A": c.col_a, "Column B": c.col_b, "Pearson r": c.coefficient, "Confidence": c.evidence.confidence}
                for c in corr_res
            ]
            st.dataframe(pd.DataFrame(corr_df_list), use_container_width=True)

# -----------------------------------------------------------------------------
# TAB 4: ANOMALY DETECTION
# -----------------------------------------------------------------------------
with tab_anomalies:
    st.subheader("🔍 Tri-Method Anomaly Detection Engine")
    
    a1, a2, a3 = st.columns(3)
    with a1:
        st.metric("IQR (Tukey Fence)", f"{iqr_res.n_flagged} Flagged", help="Univariate percentile distance beyond lower/upper fences")
    with a2:
        st.metric("Z-Score Threshold", f"{zscore_res.n_flagged} Flagged", help=f"Univariate standard deviations from mean (|z| > {z_thresh})")
    with a3:
        st.metric("Isolation Forest", f"{iforest_res.n_flagged} Flagged", help="Multivariate isolation decision trees")

    st.divider()

    # Aggregate flagged anomalies table
    all_anomalies = []
    for summary in anomaly_summaries:
        for res in summary.results:
            all_anomalies.append({
                "Method": summary.method.upper(),
                "Column": res.column,
                "Row Index": res.row_index,
                "Value": str(res.value),
                "Anomaly Score": res.score,
                "Evidence Metric": res.evidence.metric,
                "Confidence": res.evidence.confidence,
                "Calculation": res.evidence.calculation,
            })

    if not all_anomalies:
        st.success("🎉 No anomalies detected by any of the 3 statistical/ML methods!")
    else:
        st.markdown(f"#### Total Flagged Instances: **{len(all_anomalies)}**")
        anom_df = pd.DataFrame(all_anomalies)
        st.dataframe(
            anom_df[["Method", "Column", "Row Index", "Value", "Anomaly Score", "Confidence"]],
            use_container_width=True,
        )

        st.markdown("#### 🔍 Row-Level Anomaly Evidence Inspector")
        row_sel = st.selectbox(
            "Select flagged instance to inspect evidence object:",
            options=range(len(all_anomalies)),
            format_func=lambda i: f"Row #{all_anomalies[i]['Row Index']} | {all_anomalies[i]['Method']} | {all_anomalies[i]['Column']} (Value: {all_anomalies[i]['Value']})",
        )
        selected_anom = all_anomalies[row_sel]
        st.markdown(f"**Exact Math / Reasoning:**")
        st.code(selected_anom["Calculation"], language="text")

# -----------------------------------------------------------------------------
# TAB 5: VISUALIZATIONS
# -----------------------------------------------------------------------------
with tab_charts:
    st.subheader("📉 Auto-Generated Visualizations & Anomaly Highlight Plots")
    st.caption("Flagged anomaly points are highlighted with red 'X' markers.")

    if not chart_specs:
        st.info("No charts generated for this dataset.")
    else:
        for spec in chart_specs:
            fig = render_chart(spec, df)
            st.plotly_chart(fig, use_container_width=True)

# -----------------------------------------------------------------------------
# TAB 6: EVIDENCE AUDIT LOG
# -----------------------------------------------------------------------------
with tab_evidence:
    st.subheader("📜 Verifiable Evidence Audit Log")
    st.write(
        "Every single metric in DataPilot is bound to an immutable `EvidenceObject` "
        "containing the source tool, exact calculation string, row count, dataset version hash, and confidence score."
    )

    audit_bundle = {
        "dataset_version": ingestion_res.dataset_version,
        "filename": ingestion_res.filename,
        "n_rows": ingestion_res.n_rows,
        "quality_report": quality_rep.model_dump(),
        "stats": [s.model_dump() for s in stats_res],
        "correlations": [c.model_dump() for c in corr_res],
        "anomalies": [s.model_dump() for s in anomaly_summaries],
    }

    st.download_button(
        label="📥 Download Complete Evidence Bundle (JSON)",
        data=json.dumps(audit_bundle, indent=2),
        file_name=f"datapilot_evidence_{ingestion_res.dataset_version[:8]}.json",
        mime="application/json",
    )

    st.json(audit_bundle)
