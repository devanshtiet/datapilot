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
from pathlib import Path
import pandas as pd
import streamlit as st

from app.agents.planner import llm_provider_status, run_analysis_agent
from app.data.ingestion import load_file, IngestionError
from app.visualization.chart_selector import select_charts, render_chart

# Page Configuration
st.set_page_config(
    page_title="DataPilot — Agentic Data Profiler & Anomaly Detector",
    page_icon="D",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling (Industrial instrument panel)
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');
    :root {
        --chassis: #e0e5ec;
        --panel: #f0f2f5;
        --recess: #d1d9e6;
        --ink: #2d3436;
        --muted: #4a5568;
        --line: #babecc;
        --deep: #a3b1c6;
        --accent: #ff4757;
        --text-color: #2d3436;
        --background-color: #e0e5ec;
        --secondary-background-color: #d1d9e6;
        --primary-color: #ff4757;
        --shadow-card: 7px 7px 14px #babecc, -7px -7px 14px #ffffff;
        --shadow-float: 10px 10px 20px #babecc, -10px -10px 20px #ffffff, inset 1px 1px 0 rgba(255,255,255,.55);
        --shadow-recess: inset 4px 4px 8px #babecc, inset -4px -4px 8px #ffffff;
    }
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; color: var(--ink); }
    .stApp { background: var(--chassis); background-image: radial-gradient(ellipse at 8% 0%, rgba(255,255,255,.7), transparent 46%); }
    .stApp, .stApp p, .stApp label, .stApp [data-testid="stMarkdownContainer"],
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"],
    [data-testid="stSidebar"] label, [data-testid="stSidebar"] p { color: var(--ink); }
    [data-testid="stHeader"] { background: rgba(224,229,236,.9); }
    [data-testid="stSidebar"] { background: var(--chassis); border-right: 1px solid rgba(163,177,198,.6); box-shadow: 5px 0 14px rgba(163,177,198,.18); }
    [data-testid="stSidebar"] > div:first-child { padding-top: 1.6rem; }
    h1, h2, h3, h4, h5, h6 { font-family: 'Inter', sans-serif !important; letter-spacing: -.035em; color: var(--ink) !important; font-weight: 700; }
    h2 { font-size: 1.8rem !important; }
    h4 { font-size: 1.15rem !important; margin-top: 1.25rem !important; }
    code, pre, [data-testid="stMetricValue"], .metric-pill-val { font-family: 'JetBrains Mono', monospace !important; }
    .block-container { max-width: 1440px; padding-top: 2rem; }
    [data-testid="stHorizontalBlock"] { gap: 1.1rem; }
    [data-testid="stVerticalBlock"] { gap: 1rem; }
    [data-testid="stTabs"] [role="tablist"] { gap: .45rem; border-bottom: 0; padding: .5rem .65rem; border-radius: 12px; background: var(--recess); box-shadow: var(--shadow-recess); }
    [data-testid="stTabs"] button[role="tab"] { color: var(--muted); font-size: .78rem; font-weight: 700; padding: .72rem .85rem; border-radius: 8px; transition: transform .16s ease, box-shadow .16s ease, color .16s ease; }
    [data-testid="stTabs"] button[aria-selected="true"] { color: #fff; background: var(--accent); box-shadow: 3px 3px 7px rgba(166,50,60,.3), -2px -2px 6px rgba(255,255,255,.65); }
    [data-testid="stTabs"] button:active { transform: translateY(2px); }
    [data-testid="stDataFrame"], [data-testid="stPlotlyChart"] { border: 1px solid rgba(255,255,255,.72); border-radius: 12px; background: var(--panel); box-shadow: var(--shadow-card); overflow: hidden; }
    [data-testid="stMetric"] { background: var(--panel); border: 1px solid rgba(255,255,255,.7); border-radius: 12px; padding: 1rem; box-shadow: var(--shadow-card); }
    [data-testid="stMetricLabel"] { color: var(--muted); font-size: .68rem; text-transform: uppercase; letter-spacing: .08em; font-family: 'JetBrains Mono', monospace; font-weight: 600; }
    [data-testid="stMetricValue"] { color: var(--ink); }
    .stButton button, .stDownloadButton button { min-height: 44px; border-radius: 8px; border: 1px solid rgba(255,255,255,.65); background: var(--accent); color: #fff; font-weight: 800; text-transform: uppercase; letter-spacing: .055em; box-shadow: 4px 4px 8px rgba(166,50,60,.3), -3px -3px 8px rgba(255,255,255,.72); transition: transform .15s ease, box-shadow .15s ease, filter .15s ease; }
    .stButton button:hover, .stDownloadButton button:hover { border-color: white; background: var(--accent); color: white; filter: brightness(1.06); box-shadow: var(--shadow-float); }
    .stButton button:active, .stDownloadButton button:active { transform: translateY(2px); box-shadow: inset 4px 4px 8px rgba(166,50,60,.35), inset -3px -3px 7px rgba(255,255,255,.38); }
    .stButton button:focus-visible, .stDownloadButton button:focus-visible, input:focus-visible { outline: 2px solid var(--accent); outline-offset: 3px; }
    [data-testid="stExpander"] { border: 1px solid rgba(255,255,255,.7); border-radius: 12px; background: var(--panel); box-shadow: var(--shadow-card); }
    [data-testid="stExpander"] summary { min-height: 48px; padding: .65rem 1rem; }
    [data-testid="column"] { min-width: 0 !important; }
    [data-testid="stCodeBlock"], [data-testid="stJson"] { width: 100%; max-width: 100%; min-width: 0; box-sizing: border-box; overflow-x: hidden; }
    [data-testid="stCodeBlock"] pre, [data-testid="stCodeBlock"] code,
    [data-testid="stJson"] pre, [data-testid="stJson"] code,
    [data-testid="stJson"] * { white-space: pre-wrap !important; overflow-wrap: anywhere !important; word-break: break-word !important; }
    [data-testid="stTextInput"] input, [data-testid="stNumberInput"] input, [data-testid="stFileUploader"] section { background: var(--chassis); border: 0; border-radius: 8px; box-shadow: var(--shadow-recess); color: var(--ink); }
    [data-testid="stFileUploader"] section { padding: 1rem; }
    [data-testid="stSlider"] [role="slider"] { border-color: var(--accent); box-shadow: 0 0 0 5px rgba(255,71,87,.16); }
    .stProgress > div > div { background: var(--accent); }
    @keyframes rise-in { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
    .main-header, [data-testid="stTabs"] { animation: rise-in .55s cubic-bezier(.175,.885,.32,1.15) both; }
    @media (prefers-reduced-motion: reduce) { *, *::before, *::after { animation-duration: .01ms !important; } }

    /* Molded instrument bezel */
    .main-header {
        position: relative; overflow: hidden;
        background: linear-gradient(145deg, #343e42, #252d30); padding: 1.5rem 2rem 1.6rem;
        border-radius: 16px; color: #fff; margin-bottom: 1.5rem;
        border: 4px solid #c6ced8; box-shadow: 8px 8px 16px #babecc, -7px -7px 16px #fff, inset 1px 1px 0 rgba(255,255,255,.14);
        background-image: radial-gradient(circle at 13px 13px, #14191b 0 3px, #667278 3px 4px, transparent 5px), radial-gradient(circle at calc(100% - 13px) 13px, #14191b 0 3px, #667278 3px 4px, transparent 5px), linear-gradient(145deg, #343e42, #252d30);
    }
    .main-header::after { content: ''; position: absolute; right: 1.4rem; bottom: 1rem; width: 52px; height: 25px; opacity: .38; background: repeating-linear-gradient(90deg, transparent 0 5px, #aab6bd 5px 7px); border-radius: 4px; box-shadow: inset 1px 1px 3px #111; }
    .main-header h1 {
        margin: 0; font-size: clamp(2rem, 5vw, 3.15rem); font-weight: 800;
        color: #fff !important; font-family: 'Inter', sans-serif !important; text-shadow: 0 2px 4px rgba(0,0,0,.35);
    }
    .main-header p {
        margin: .5rem 0 0; color: #d5dde0; font-size: .72rem;
        letter-spacing: .11em; font-family: 'JetBrains Mono', monospace;
    }
    .main-header p { color: #d5dde0 !important; }
    .glass-card {
        background: var(--panel); border: 1px solid rgba(255,255,255,.72);
        border-radius: 16px; padding: 1.25rem 1.5rem; margin-bottom: 1.25rem; box-shadow: var(--shadow-card);
    }
    .score-badge-high { color: #397859; font-weight: 600; font-size: 2.8rem; font-family: 'JetBrains Mono', monospace; }
    .score-badge-medium { color: #a36b18; font-weight: 600; font-size: 2.8rem; font-family: 'JetBrains Mono', monospace; }
    .score-badge-low { color: var(--accent); font-weight: 600; font-size: 2.8rem; font-family: 'JetBrains Mono', monospace; }
    .metric-pill {
        position: relative; background: var(--panel); border-radius: 12px; padding: .95rem 1rem;
        text-align: left; border: 1px solid rgba(255,255,255,.75); box-shadow: var(--shadow-card); transition: transform .25s cubic-bezier(.175,.885,.32,1.15), box-shadow .25s ease;
    }
    .metric-pill:hover { transform: translateY(-3px); box-shadow: var(--shadow-float); }
    .metric-pill-val {
        font-size: 1.4rem; font-weight: 600; color: var(--ink); font-family: 'JetBrains Mono', monospace;
    }
    .metric-pill-lbl {
        font-size: .65rem; color: var(--muted); text-transform: uppercase; letter-spacing: .08em; margin-top: .4rem; font-family: 'JetBrains Mono', monospace; font-weight: 600;
    }
    .quality-score-panel { min-height: 174px; display: flex; flex-direction: column; justify-content: center; margin: .35rem 0 1.2rem; padding: 1.5rem; }
    .quality-dimension { min-height: 248px; padding: 1.2rem !important; margin-bottom: .75rem !important; }
    .quality-dimension-score { margin-top: .55rem; line-height: 1.2; }
    .quality-dimension-reason { margin-top: .7rem !important; line-height: 1.65; }
    [data-testid="stTabs"] [role="tabpanel"] { padding-top: 1.35rem; }
    .stDivider { border-color: rgba(163,177,198,.65); }
    @media (max-width: 640px) { .main-header { padding: 1.3rem 1.2rem; } .metric-pill { padding: .75rem; } .metric-pill-val { font-size: 1rem; } }
    </style>
    """,
    unsafe_allow_html=True,
)

# Masthead
st.markdown(
    """
    <div class="main-header">
        <h1>DataPilot <span style="color:#ff4757">/</span> ANALYSIS UNIT</h1>
        <p><span style="display:inline-block;width:9px;height:9px;border-radius:50%;background:#55d68b;box-shadow:0 0 9px #55d68b;margin-right:8px"></span> SYSTEM OPERATIONAL &nbsp;·&nbsp; QUALITY CONTROL &nbsp;·&nbsp; ANOMALY DETECTION</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# Sidebar configuration & upload
with st.sidebar:
    st.header("Data Source")
    data_source = st.radio(
        "Choose Data Source:",
        [
            "Sample: Messy Data (Outliers & Missing Values)",
            "Sample: Clean Data (Benchmark)",
            "Upload Custom File (CSV, Excel)",
        ],
        index=0,
    )

    file_bytes: bytes | None = None
    filename: str = ""

    samples_dir = Path(__file__).parent.parent / "scripts" / "sample_data"

    if data_source == "Sample: Messy Data (Outliers & Missing Values)":
        messy_path = samples_dir / "messy_data.csv"
        if messy_path.exists():
            file_bytes = messy_path.read_bytes()
            filename = "messy_data.csv"
            st.caption("Loaded 500+ rows with missing values, duplicates, and 5 injected extreme outliers.")
        else:
            st.warning("Sample messy dataset not found. Please generate it using scripts/generate_synthetic_data.py")
    elif data_source == "Sample: Clean Data (Benchmark)":
        clean_path = samples_dir / "clean_data.csv"
        if clean_path.exists():
            file_bytes = clean_path.read_bytes()
            filename = "clean_data.csv"
            st.caption("Loaded clean synthetic dataset with realistic correlations and 0 nulls.")
        else:
            st.warning("Sample clean dataset not found. Please generate it using scripts/generate_synthetic_data.py")
    else:
        uploaded_file = st.file_uploader(
            "Upload a dataset (CSV, XLSX, XLS)",
            type=["csv", "xlsx", "xls"],
            help="Maximum size: 200MB. Supported formats: CSV, Excel",
        )
        if uploaded_file is not None:
            file_bytes = uploaded_file.getvalue()
            filename = uploaded_file.name
    
    st.divider()
    st.markdown("### Engine Parameters")
    z_thresh = st.slider("Z-Score Threshold", 1.5, 5.0, 3.0, 0.1)
    iqr_mult = st.slider("IQR Multiplier (Tukey Fence)", 1.0, 3.0, 1.5, 0.1)
    st.caption("All numbers displayed originate from deterministic Python/ML tool calls backed by verifiable Evidence Objects.")

    selected_provider, llm_ready = llm_provider_status()
    if llm_ready and selected_provider:
        use_hosted_llm = st.checkbox(
            f"Use {selected_provider.title()} for AI interpretation",
            value=False,
            help=(
                "When enabled, DataPilot sends aggregate quality/statistical results and column names "
                "to the selected provider. Raw dataset rows and sample values are not sent."
            ),
        )
        st.caption("Hosted interpretation is optional; numeric results always come from local analysis tools.")
    else:
        use_hosted_llm = False
        st.caption("AI interpretation is not configured. Add a provider key to .env to enable it.")

if file_bytes is None:
    st.info("Please select a sample dataset or upload a CSV/Excel file from the sidebar to start profiling.")
    st.stop()

# Execution Pipeline
try:
    with st.spinner("Ingesting and parsing file..."):
        df, ingestion_res = load_file(file_bytes, filename)
except IngestionError as err:
    st.error(f"Ingestion Error: {err}")
    st.stop()
except Exception as err:
    st.error(f"Unexpected Error during ingestion: {err}")
    st.stop()

# Run the graph's deterministic tools; hosted interpretation runs only after explicit opt-in.
try:
    with st.spinner("DataPilot agent is profiling the dataset..."):
        analysis = run_analysis_agent(
            df,
            ingestion_res.dataset_version,
            ingestion_res.filename,
            zscore_threshold=z_thresh,
            iqr_multiplier=iqr_mult,
            use_hosted_llm=use_hosted_llm,
        )
except Exception as err:
    st.error(f"Analysis workflow failed: {err}")
    st.stop()

quality_rep = analysis["quality_report"]
stats_res = analysis["stats"]
corr_res = analysis["correlations"]
anomaly_summaries = analysis["anomaly_summaries"]
iqr_res, zscore_res, iforest_res = anomaly_summaries
agent_insight = analysis["insight"]

# Step 5: Visualizations Selection
chart_specs = select_charts(df, quality_rep, anomaly_summaries, corr_res, stats_res)

# Layout Tabs
tab_overview, tab_agent, tab_quality, tab_stats, tab_anomalies, tab_charts, tab_evidence = st.tabs([
    "Dataset Overview",
    "Agent Insights",
    "Data Quality Score",
    "Descriptive Stats",
    "Anomaly Detection",
    "Visualizations",
    "Evidence Audit Log",
])

# -----------------------------------------------------------------------------
# TAB 1: OVERVIEW
# -----------------------------------------------------------------------------
with tab_overview:
    st.subheader("Dataset Overview")
    
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
# TAB 2: AGENT INSIGHTS
# -----------------------------------------------------------------------------
with tab_agent:
    st.subheader("Evidence-Grounded Agent Insights")
    mode_label = "Hosted AI interpretation" if agent_insight.generation_mode == "llm" else "Local evidence summary"
    st.caption(f"{mode_label}" + (f" via {agent_insight.provider.title()}" if agent_insight.provider else ""))
    st.markdown(agent_insight.summary)
    for finding in agent_insight.findings:
        st.markdown(f"- {finding}")
    if agent_insight.notice:
        st.info(agent_insight.notice)
    st.caption("The agent summarizes measured results; scores, statistics, correlations, and flags are computed by deterministic tools.")

# -----------------------------------------------------------------------------
# TAB 3: DATA QUALITY SCORECARD
# -----------------------------------------------------------------------------
with tab_quality:
    st.subheader("Data Quality Scorecard")
    
    score = quality_rep.composite_score
    badge_cls = "score-badge-high" if score >= 80 else ("score-badge-medium" if score >= 60 else "score-badge-low")
    
    col_score, col_summary = st.columns([1, 2])
    with col_score:
        st.markdown(
            f"""
            <div class="quality-score-panel" style="text-align: center; background: #f0f2f5; border-radius: 16px; border: 1px solid #ffffff; box-shadow: inset 4px 4px 8px #babecc, inset -4px -4px 8px #ffffff;">
                <div style="color: #4a5568; font-size: 0.72rem; text-transform: uppercase; letter-spacing: .1em; font-family: 'JetBrains Mono', monospace;">Composite Data Quality Score</div>
                <div class="{badge_cls}">{score:.1f}<span style="font-size: 1.05rem; color: #4a5568;">/100</span></div>
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
            d_cls = "#397859" if d_score >= 80 else ("#a36b18" if d_score >= 60 else "#ff4757")
            st.markdown(
                f"""
                <div class="quality-dimension" style="background: #f0f2f5; border-radius: 14px; border: 1px solid #ffffff; border-left: 4px solid {d_cls}; box-shadow: 6px 6px 12px #babecc, -6px -6px 12px #ffffff;">
                    <div style="font-weight: 600; text-transform: capitalize;">{dim.name}</div>
                    <div class="quality-dimension-score" style="font-size: 1.6rem; font-weight: 700; color: {d_cls};">{d_score:.1f}%</div>
                    <div class="quality-dimension-reason" style="font-size: 0.8rem; color: #4a5568;">{dim.reason}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            with st.expander(f"Evidence for {dim.name}"):
                st.code(dim.evidence.calculation, language="text")
                st.json(dim.evidence.model_dump())

# -----------------------------------------------------------------------------
# TAB 4: DESCRIPTIVE STATISTICS
# -----------------------------------------------------------------------------
with tab_stats:
    st.subheader("Statistical Profile")
    
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

        st.markdown("#### Evidence Traceability for Column Stats")
        selected_stat_col = st.selectbox("Select column to view stat calculation details:", [s.column for s in stats_res])
        selected_stat = next(s for s in stats_res if s.column == selected_stat_col)
        st.info(f"**Calculation Formula:** {selected_stat.evidence.calculation}")
        st.json(selected_stat.evidence.model_dump())

        if corr_res:
            st.markdown("#### Pearson Correlation Matrix")
            corr_df_list = [
                {"Column A": c.col_a, "Column B": c.col_b, "Pearson r": c.coefficient, "Confidence": c.evidence.confidence}
                for c in corr_res
            ]
            st.dataframe(pd.DataFrame(corr_df_list), use_container_width=True)

# -----------------------------------------------------------------------------
# TAB 5: ANOMALY DETECTION
# -----------------------------------------------------------------------------
with tab_anomalies:
    st.subheader("Tri-Method Anomaly Detection Engine")
    
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
        st.success("No anomalies detected by any of the 3 statistical/ML methods!")
    else:
        st.markdown(f"#### Total Flagged Instances: **{len(all_anomalies)}**")
        anom_df = pd.DataFrame(all_anomalies)
        st.dataframe(
            anom_df[["Method", "Column", "Row Index", "Value", "Anomaly Score", "Confidence"]],
            use_container_width=True,
        )

        st.markdown("#### Row-Level Anomaly Evidence Inspector")
        row_sel = st.selectbox(
            "Select flagged instance to inspect evidence object:",
            options=range(len(all_anomalies)),
            format_func=lambda i: f"Row #{all_anomalies[i]['Row Index']} | {all_anomalies[i]['Method']} | {all_anomalies[i]['Column']} (Value: {all_anomalies[i]['Value']})",
        )
        selected_anom = all_anomalies[row_sel]
        st.markdown(f"**Exact Math / Reasoning:**")
        st.code(selected_anom["Calculation"], language="text")

# -----------------------------------------------------------------------------
# TAB 6: VISUALIZATIONS
# -----------------------------------------------------------------------------
with tab_charts:
    st.subheader("Auto-Generated Visualizations & Anomaly Highlight Plots")
    st.caption("Flagged anomaly points are highlighted with red 'X' markers.")

    if not chart_specs:
        st.info("No charts generated for this dataset.")
    else:
        for spec in chart_specs:
            fig = render_chart(spec, df)
            st.plotly_chart(fig, use_container_width=True)

# -----------------------------------------------------------------------------
# TAB 7: EVIDENCE AUDIT LOG
# -----------------------------------------------------------------------------
with tab_evidence:
    st.subheader("Verifiable Evidence Audit Log")
    st.write(
        "Every single metric in DataPilot is bound to an immutable `EvidenceObject` "
        "containing the source tool, exact calculation string, row count, dataset version hash, and confidence score."
    )

    audit_bundle = {
        "dataset_version": ingestion_res.dataset_version,
        "filename": ingestion_res.filename,
        "n_rows": ingestion_res.n_rows,
        "quality_report": quality_rep.model_dump(),
        "agent_insight": agent_insight.model_dump(),
        "stats": [s.model_dump() for s in stats_res],
        "correlations": [c.model_dump() for c in corr_res],
        "anomalies": [s.model_dump() for s in anomaly_summaries],
    }

    st.download_button(
        label="Download Complete Evidence Bundle (JSON)",
        data=json.dumps(audit_bundle, indent=2),
        file_name=f"datapilot_evidence_{ingestion_res.dataset_version[:8]}.json",
        mime="application/json",
    )

    st.json(audit_bundle)
