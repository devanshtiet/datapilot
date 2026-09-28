import React, { useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

const sections = [
  ["overview", "Overview", "01"],
  ["quality", "Quality profile", "02"],
  ["statistics", "Statistics", "03"],
  ["anomalies", "Anomalies", "04"],
  ["explore", "Visual explorer", "05"],
  ["compare", "Compare runs", "06"],
  ["insight", "Agent notes", "07"],
  ["repairs", "Repair copilot", "08"],
  ["audit", "Evidence ledger", "09"],
];

async function readApiResponse(response) {
  const text = await response.text();
  let body = {};
  if (text) {
    try { body = JSON.parse(text); }
    catch {
      const preview = text.replace(/\s+/g, " ").slice(0, 180);
      throw new Error(`The analysis service returned an unreadable response (HTTP ${response.status}). ${preview || "The server returned an empty response."}`);
    }
  }
  if (!response.ok) throw new Error(body.detail || `The analysis service returned HTTP ${response.status}.`);
  if (!text) throw new Error("The analysis service returned an empty response.");
  return body;
}

const pretty = (value) => {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "number") return value.toLocaleString(undefined, { maximumFractionDigits: 3 });
  return String(value);
};

function App() {
  const [section, setSection] = useState("overview");
  const [report, setReport] = useState(null);
  const [previousReport, setPreviousReport] = useState(null);
  const [previousFilename, setPreviousFilename] = useState("");
  const [columnFilter, setColumnFilter] = useState("");
  const [sortBy, setSortBy] = useState("missing");
  const [anomalyMethod, setAnomalyMethod] = useState("all");
  const [sourceFile, setSourceFile] = useState(null);
  const [repairCandidates, setRepairCandidates] = useState(null);
  const [repairPreview, setRepairPreview] = useState(null);
  const [repairError, setRepairError] = useState("");
  const [repairBusy, setRepairBusy] = useState(false);
  const [repairDownload, setRepairDownload] = useState("");
  const [useGroq, setUseGroq] = useState(false);
  const [selectedRepairs, setSelectedRepairs] = useState([]);
  const [filename, setFilename] = useState("");
  const [busy, setBusy] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState("");
  const [zscore, setZscore] = useState(3);
  const [iqr, setIqr] = useState(1.5);
  const [selectedStat, setSelectedStat] = useState(0);
  const inputRef = useRef(null);

  async function analyze(file) {
    if (!file) return;
    setError("");
    if (!/\.(csv|xlsx|xls)$/i.test(file.name)) {
      setError("Choose a CSV, XLSX, or XLS file.");
      return;
    }
    if (file.size > 4 * 1024 * 1024) {
      setError("This Vercel deployment accepts files up to 4 MB.");
      return;
    }

    setBusy(true);
    setFilename(file.name);
    setSourceFile(file);
    setRepairCandidates(null);
    setRepairPreview(null);
    setRepairDownload("");
    setSelectedRepairs([]);
    try {
      const query = new URLSearchParams({ filename: file.name, zscore_threshold: String(zscore), iqr_multiplier: String(iqr) });
      const response = await fetch(`/api/profile?${query}`, {
        method: "POST",
        headers: { "Content-Type": "application/octet-stream" },
        body: file,
      });
      const body = await readApiResponse(response);
      if (report && report.dataset.dataset_version !== body.dataset.dataset_version) {
        setPreviousReport(report);
        setPreviousFilename(filename);
      }
      setReport(body);
      setSection("overview");
      setSelectedStat(0);
    } catch (exception) {
      const message = exception.message || "The dataset could not be analyzed. Try again.";
      setError(/fetch|network/i.test(message) ? "The analysis API is not responding. Start the DataPilot API on port 8000, then retry." : message);
    } finally {
      setBusy(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  async function requestRepairs(stage, ids = selectedRepairs) {
    if (!sourceFile) return;
    setRepairBusy(true);
    setRepairError("");
    try {
      const query = new URLSearchParams({ filename: sourceFile.name });
      let endpoint = "/api/repairs/propose";
      if (stage === "propose") query.set("use_groq", String(useGroq));
      if (stage === "preview") { endpoint = "/api/repairs/preview"; query.set("selected", JSON.stringify(ids)); }
      if (stage === "apply") { endpoint = "/api/repairs/apply"; query.set("selected", JSON.stringify(ids)); }
      const response = await fetch(`${endpoint}?${query}`, {
        method: "POST",
        headers: { "Content-Type": "application/octet-stream" },
        body: sourceFile,
      });
      if (stage === "apply") {
        if (!response.ok) await readApiResponse(response);
        const blobUrl = URL.createObjectURL(await response.blob());
        const link = document.createElement("a");
        link.href = blobUrl;
        link.download = `${sourceFile.name.replace(/\.csv$/i, "")}_repaired.csv`;
        link.click();
        window.setTimeout(() => URL.revokeObjectURL(blobUrl), 1000);
        setRepairDownload(link.download);
      } else {
        const body = await readApiResponse(response);
        if (stage === "propose") {
          setRepairCandidates(body);
          setSelectedRepairs([]);
          setRepairPreview(null);
          setRepairDownload("");
        } else {
          setRepairPreview(body);
          setRepairDownload("");
        }
      }
    } catch (exception) {
      setRepairError(exception.message || "The repair request could not be completed.");
    } finally {
      setRepairBusy(false);
    }
  }

  async function loadExample() {
    setError("");
    setBusy(true);
    try {
      const response = await fetch("/sample_data/retail_orders_demo.csv");
      if (!response.ok) throw new Error("The sample dataset could not be loaded.");
      const file = new File([await response.blob()], "retail_orders_demo.csv", { type: "text/csv" });
      await analyze(file);
    } catch (exception) {
      setError(exception.message || "The sample dataset could not be loaded.");
      setBusy(false);
    }
  }

  const dimensions = report?.quality_report?.dimensions ?? [];
  const stats = report?.statistics ?? [];
  const correlations = report?.correlations ?? [];
  const anomalies = report?.anomalies ?? [];
  const totalFlagged = report?.unique_flagged_count ?? new Set(anomalies.flatMap(item => (item.results ?? []).map(hit => `${hit.row_index}:${hit.column}`))).size;
  const overlappingFlags = report?.overlapping_flag_count ?? 0;
  const selectedStatEvidence = stats[selectedStat]?.evidence;

  const auditBundle = useMemo(() => report ? JSON.stringify(report, null, 2) : "", [report]);

  function downloadAudit() {
    const url = URL.createObjectURL(new Blob([auditBundle], { type: "application/json" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = `datapilot-audit-${report.dataset.dataset_version.slice(0, 8)}.json`;
    link.click();
    URL.revokeObjectURL(url);
  }

  const score = report?.quality_report?.composite_score ?? 0;
  const scoreClass = score >= 80 ? "good" : score >= 60 ? "watch" : "low";

  return (
    <div className="app-shell">
      <aside className="rail">
        <a className="brand" href="#top" onClick={() => setSection("overview")} aria-label="DataPilot home">
          <img className="brand-mark-image" src="/datapilot-mark.svg" alt="" />
          <span className="brand-name">data<span>pilot</span><small>DATA OBSERVATORY</small></span>
        </a>
        <div className="rail-rule" />
        <div className="rail-label">WORKSPACE</div>
        <nav className="nav-list" aria-label="Analysis sections">
          {sections.map(([id, label, number]) => (
            <button key={id} className={`nav-item ${section === id ? "active" : ""}`} onClick={() => setSection(id)} disabled={!report && id !== "overview"}>
              <span className="nav-number">{number}</span><span>{label}</span>
              {section === id && <span className="nav-indicator" />}
            </button>
          ))}
        </nav>
        <div className="rail-bottom">
          <span className="status-light" />
          <div><strong>ANALYSIS ENGINE</strong><small>Deterministic mode</small></div>
        </div>
      </aside>

      <main className="main-area" id="top">
        <header className="topbar">
          <div className="breadcrumbs"><span>WORKSPACE</span><span className="slash">/</span><strong>{report ? filename : "New analysis"}</strong></div>
          <div className="topbar-actions">
            <a className="api-link" href="/api/docs" target="_blank" rel="noreferrer">API reference <span>↗</span></a>
            {report && <button className="button button-dark button-small print-button" onClick={() => window.print()}>Export report / PDF</button>}
            {report && <button className="button button-dark button-small" onClick={() => inputRef.current?.click()}>Analyze another file</button>}
          </div>
          <input ref={inputRef} className="visually-hidden" type="file" accept=".csv,.xlsx,.xls" onChange={(event) => analyze(event.target.files?.[0])} />
        </header>

        {report && <div className="print-report"><PrintReport report={report}/></div>}

        {!report ? (
          <section className="welcome-wrap">
            <div className="eyebrow"><span className="eyebrow-line" /> DATA QUALITY, MADE LEGIBLE <span className="eyebrow-line" /></div>
            <h1>Know what your<br /><em>data is saying.</em></h1>
            <p className="welcome-copy">A clear-eyed profile of completeness, consistency, and unusual values — every finding traceable to its calculation.</p>
            <div className={`drop-card ${dragging ? "dragging" : ""}`} onDragOver={(event) => { event.preventDefault(); setDragging(true); }} onDragLeave={() => setDragging(false)} onDrop={(event) => { event.preventDefault(); setDragging(false); analyze(event.dataTransfer.files?.[0]); }}>
              <div className="upload-stamp"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 16V4m0 0L7.5 8.5M12 4l4.5 4.5M4.5 15v4.5h15V15" /></svg></div>
              <div className="drop-copy"><strong>{busy ? "Reading your dataset" : "Drop a dataset here"}</strong><span>{busy ? "Checking columns, quality, and outliers." : "CSV, XLSX, or XLS · up to 4 MB"}</span></div>
              <button className="button button-dark" onClick={() => inputRef.current?.click()} disabled={busy}>{busy ? <span className="spinner" /> : "Choose file"}</button>
              {busy && <div className="progress-track"><span /></div>}
            </div>
            {error && <p className="error-message" role="alert">{error}</p>}
            <div className="welcome-divider"><span>OR START WITH AN EXAMPLE</span></div>
            <button className="sample-link" onClick={loadExample} disabled={busy}>Load the retail orders sample <span aria-hidden="true">→</span></button>
            <div className="privacy-note"><span className="lock-glyph" aria-hidden="true">⌑</span> Uploads are processed for this analysis and DataPilot does not save the uploaded file. Raw rows are not sent to an AI provider; optional repair explanations share column names and issue counts only.</div>
          </section>
        ) : (
          <>
            <section className="page-heading">
              <div><div className="eyebrow left"><span className="eyebrow-line" /> DATASET REVIEW</div><h1>{sections.find(([id]) => id === section)?.[1] ?? "Overview"}</h1><p>{filename} <span className="heading-dot">·</span> {pretty(report.dataset.n_rows)} rows <span className="heading-dot">·</span> {report.dataset.n_cols} columns</p></div>
              <div className={`score-chip ${scoreClass}`}><span className="score-chip-label">OVERALL QUALITY</span><strong>{score.toFixed(1)}<small> / 100</small></strong></div>
            </section>
            {section === "overview" && <Overview report={report} scoreClass={scoreClass} totalFlagged={totalFlagged} onNavigate={setSection} />}
            {section === "quality" && <Quality report={report} scoreClass={scoreClass} />}
            {section === "statistics" && <Statistics stats={stats} correlations={correlations} selected={selectedStat} setSelected={setSelectedStat} evidence={selectedStatEvidence} visualProfile={report.visual_profile} />}
            {section === "anomalies" && <Anomalies anomalies={anomalies} totalFlagged={totalFlagged} overlappingFlags={overlappingFlags} rowContext={report.row_context} method={anomalyMethod} setMethod={setAnomalyMethod} zscore={zscore} setZscore={setZscore} iqr={iqr} setIqr={setIqr} onReanalyze={() => analyze(sourceFile)} busy={busy} />}
            {section === "explore" && <Explorer report={report} filter={columnFilter} setFilter={setColumnFilter} sortBy={sortBy} setSortBy={setSortBy} />}
            {section === "compare" && <Compare report={report} previous={previousReport} previousFilename={previousFilename} />}
            {section === "insight" && <Insight insight={report.insight} />}
            {section === "repairs" && <RepairCopilot file={sourceFile} candidates={repairCandidates} preview={repairPreview} error={repairError} busy={repairBusy} download={repairDownload} useGroq={useGroq} setUseGroq={setUseGroq} selected={selectedRepairs} setSelected={setSelectedRepairs} onRequest={requestRepairs} />}
            {section === "audit" && <Audit report={report} onDownload={downloadAudit} />}
          </>
        )}
        <footer className="footer"><span>DATAPILOT <i>·</i> EVIDENCE-LED ANALYSIS</span><span>NO METRIC WITHOUT ITS METHOD</span></footer>
      </main>
    </div>
  );
}

function Overview({ report, scoreClass, totalFlagged, onNavigate }) {
  const profiles = report.quality_report.column_profiles ?? [];
  return <div className="content-stack animate-in">
    <div className="metric-grid">
      <Metric label="Rows ingested" value={pretty(report.dataset.n_rows)} note="records parsed" />
      <Metric label="Fields observed" value={pretty(report.dataset.n_cols)} note="columns detected" />
      <Metric label="Data quality" value={`${report.quality_report.composite_score.toFixed(1)}`} note="out of 100" accent={scoreClass} />
      <Metric label="Anomalies flagged" value={pretty(totalFlagged)} note="across 2 detectors" />
    </div>
    <div className="overview-grid">
      <section className="panel schema-panel">
        <PanelHead kicker="STRUCTURE" title="Column register" meta={`${profiles.length} FIELDS`} />
        <div className="table-wrap"><table><thead><tr><th>FIELD</th><th>TYPE</th><th>MISSING</th><th>UNIQUE</th></tr></thead><tbody>
          {profiles.map((column) => <tr key={column.column_name}><td className="field-name">{column.column_name}</td><td><span className="type-tag">{column.dtype}</span></td><td>{column.pct_missing.toFixed(1)}%</td><td>{pretty(column.n_unique)}</td></tr>)}
        </tbody></table></div>
      </section>
      <section className="panel score-panel">
        <PanelHead kicker="QUALITY SIGNAL" title="Where to look first" />
        <div className="dimension-list">{report.quality_report.dimensions.map((dimension) => <button className="dimension-row" key={dimension.name} onClick={() => onNavigate("quality")}>
          <span className="dimension-name">{dimension.name}</span><span className="bar-track"><span style={{ width: `${dimension.score}%` }} /></span><strong>{dimension.score.toFixed(1)}</strong>
        </button>)}</div>
        <div className="hash-block"><span>DATASET FINGERPRINT</span><code>{report.dataset.dataset_version}</code></div>
      </section>
    </div>
  </div>;
}

function Quality({ report, scoreClass }) {
  const quality = report.quality_report;
  return <div className="content-stack animate-in">
    <div className="quality-intro panel"><div className="quality-score-large"><span>COMPOSITE SCORE</span><strong className={scoreClass}>{quality.composite_score.toFixed(1)}<small> / 100</small></strong><div className="score-track"><i style={{ width: `${quality.composite_score}%` }} /></div></div><p>Four deterministic checks describe how complete, unique, valid, and internally consistent this dataset is. Expand a dimension to inspect the exact evidence used.</p></div>
    <div className="quality-grid">{quality.dimensions.map((dimension, index) => <details className="panel quality-card" key={dimension.name} open={index === 0}>
      <summary><span className="card-index">0{index + 1}</span><span className="quality-title">{dimension.name}</span><strong className={dimension.score >= 80 ? "text-good" : dimension.score >= 60 ? "text-watch" : "text-low"}>{dimension.score.toFixed(1)}%</strong><p>{dimension.reason}</p><span className="expand-label">VIEW EVIDENCE <span>＋</span></span></summary>
      <div className="evidence-detail"><span>CALCULATION</span><code>{dimension.evidence.calculation}</code><EvidenceGrid evidence={dimension.evidence} /></div>
    </details>)}</div>
  </div>;
}

function Statistics({ stats, correlations, selected, setSelected, evidence, visualProfile }) {
  return <div className="content-stack animate-in">
    <section className="panel"><PanelHead kicker="NUMERIC PROFILE" title="Descriptive statistics" meta={`${stats.length} NUMERIC FIELDS`} />
      {!stats.length ? <EmptyState title="No numeric fields found" body="This dataset has no columns that can be summarized as numbers." /> : <><div className="table-wrap"><table className="wide-table"><thead><tr><th>FIELD</th><th>VALID</th><th>MEAN</th><th>MEDIAN</th><th>STD. DEV.</th><th>MIN</th><th>MAX</th></tr></thead><tbody>{stats.map((row, index) => <tr key={row.column} className={selected === index ? "selected-row" : ""} onClick={() => setSelected(index)}><td className="field-name">{row.column}</td><td>{pretty(row.n_valid)}</td><td>{pretty(row.mean)}</td><td>{pretty(row.median)}</td><td>{pretty(row.std)}</td><td>{pretty(row.min_val)}</td><td>{pretty(row.max_val)}</td></tr>)}</tbody></table></div>
      {evidence && <div className="selected-evidence"><div><span className="panel-kicker">SELECTED FIELD</span><h3>{stats[selected].column}</h3></div><code>{evidence.calculation}</code><EvidenceGrid evidence={evidence} /></div>}</>}
    </section>
    <section className="panel"><PanelHead kicker="RELATIONSHIPS" title="Correlation heatmap" meta={`${correlations.length} PAIRS`} />{correlations.length ? <CorrelationHeatmap correlations={correlations} /> : <EmptyState title="No field pairs to compare" body="Pearson correlation appears when the dataset has at least two numeric fields." />}</section>
    {stats.length > 0 && <section className="panel"><PanelHead kicker="DISTRIBUTION" title="Numeric field distributions" meta="HISTOGRAMS + BOXPLOTS" /><div className="chart-grid">{stats.map((item) => <DistributionChart key={item.column} name={item.column} profile={visualProfile?.distributions?.[item.column]} />)}</div></section>}
    {!!visualProfile?.scatter?.length && <section className="panel"><PanelHead kicker="FIELD RELATIONSHIPS" title="Scatter plots" meta="SAMPLED POINTS" /><div className="chart-grid">{visualProfile.scatter.slice(0,12).map(pair=><ScatterChart key={pair.x+pair.y} pair={pair}/>)}</div>{visualProfile.scatter.length>12&&<p className="small-note">Showing the first 12 field pairs. Each plot samples up to 250 complete observations.</p>}</section>}
    {Object.keys(visualProfile?.categories ?? {}).length > 0 && <section className="panel"><PanelHead kicker="CATEGORICAL PROFILE" title="Most common values" /><div className="chart-grid">{Object.entries(visualProfile.categories).map(([name, data]) => <CategoryChart key={name} name={name} data={data} />)}</div></section>}
  </div>;
}

function Anomalies({ anomalies, totalFlagged, overlappingFlags, rowContext, method, setMethod, zscore, setZscore, iqr, setIqr, onReanalyze, busy }) {
  const hits = anomalies.filter((x) => method === "all" || x.method === method).flatMap((x) => (x.results ?? []).map((row) => ({...row, method:x.method}))).sort((a,b) => b.score-a.score);
  function exportHits() { downloadCsv("datapilot-flagged-rows.csv", ["method","row_number","column","value","score"], hits.map(x => [x.method,x.row_index+1,x.column,x.value,x.score])); }
  return <div className="content-stack animate-in">
    <section className="anomaly-banner"><div><span className="panel-kicker">DETECTION SUMMARY</span><h2>{totalFlagged ? `${pretty(totalFlagged)} unique flagged observations` : "No unusual values surfaced"}</h2><p>Two independent detectors inspect numeric fields. {pretty(overlappingFlags)} observations were flagged by both methods; an outlier flag is a prompt to inspect, not a verdict.</p></div><div className="anomaly-total">{pretty(totalFlagged)}<small>UNIQUE ROW + FIELD FLAGS</small></div></section>
    <div className="anomaly-grid">{anomalies.map((item, index) => <section className="panel detector-card" key={item.method}><span className="card-index">DETECTOR 0{index + 1}</span><div className="detector-heading"><h3>{item.method === "iqr" ? "Interquartile range" : "Z-score"}</h3><strong>{pretty(item.n_flagged)}</strong></div><p>{item.method === "iqr" ? "Flags values beyond Tukey fences around the middle half of the distribution." : "Flags values more than the selected standard-deviation threshold from the mean."}</p><div className="detector-foot"><span>{item.columns_analysed.length} FIELDS SCANNED</span><span>{item.method === "iqr" ? "ROBUST SPREAD" : "STANDARDIZED DISTANCE"}</span></div></section>)}</div>
    <section className="panel threshold-panel"><PanelHead kicker="DETECTOR SETTINGS" title="Tune sensitivity" /><label>Z-score threshold <strong>{zscore.toFixed(1)}σ</strong><input type="range" min="1.5" max="5" step=".1" value={zscore} onChange={e=>setZscore(Number(e.target.value))}/></label><label>IQR multiplier <strong>{iqr.toFixed(1)}×</strong><input type="range" min="1" max="3" step=".1" value={iqr} onChange={e=>setIqr(Number(e.target.value))}/></label><button className="button button-dark" disabled={busy} onClick={onReanalyze}>{busy?"Reanalyzing…":"Apply thresholds"}</button></section>
    <section className="panel"><div className="panel-head"><div><span className="panel-kicker">ROW INSPECTION</span><h2>Flagged observations</h2></div><div className="inline-controls"><label>Detector <select value={method} onChange={e=>setMethod(e.target.value)}><option value="all">All detectors</option><option value="iqr">IQR</option><option value="zscore">Z-score</option></select></label><button className="button button-dark button-small" onClick={exportHits} disabled={!hits.length}>Export CSV</button></div></div><div className="table-wrap"><table><thead><tr><th>ROW</th><th>FIELD</th><th>VALUE</th><th>DETECTOR</th><th>SCORE</th><th>CONTEXT</th></tr></thead><tbody>{hits.slice(0,250).map((hit,i)=><tr key={i}><td>{hit.row_index+1}</td><td className="field-name">{hit.column}</td><td>{pretty(hit.value)}</td><td>{hit.method.toUpperCase()}</td><td>{pretty(hit.score)}</td><td>{rowContext?.[String(hit.row_index)]?<details><summary>View row</summary><div className="row-context">{Object.entries(rowContext[String(hit.row_index)]).map(([k,v])=><span key={k}><b>{k}</b>{v}</span>)}</div></details>:"Context limit reached"}</td></tr>)}</tbody></table>{hits.length>250&&<p className="small-note">Showing top 250 of {hits.length}. CSV export contains all returned findings.</p>}{!hits.length&&<EmptyState title="No matching observations" body="Try another detector or threshold."/>}</div><p className="small-note">Row context is returned for up to the first 100 unique flagged rows to keep responses compact.</p></section>
  </div>;
}

function Insight({ insight }) {
  return <div className="content-stack animate-in">
    <section className="insight-hero"><span className="panel-kicker">EVIDENCE-GROUNDED SUMMARY</span><h2>{insight.summary}</h2><p>{insight.notice}</p></section>
    <section className="panel"><PanelHead kicker="OBSERVATIONS" title="What the profile shows" meta="RULE-GENERATED" /><div className="finding-list">{(insight.findings ?? []).map((finding, index) => <div className="finding" key={finding}><span>0{index + 1}</span><p>{finding}</p></div>)}</div></section>
    <div className="notice-strip"><span className="notice-rule" />Every statement here comes from measured quality metrics. Numeric results stay deterministic; no rows are sent to an LLM.</div>
  </div>;
}

function RepairCopilot({ file, candidates, preview, error, busy, download, useGroq, setUseGroq, selected, setSelected, onRequest }) {
  const isCsv = file?.name?.toLowerCase().endsWith(".csv");
  const toggle = (id) => {
    setSelected((current) => current.includes(id) ? current.filter((item) => item !== id) : [...current, id]);
  };
  return <div className="content-stack animate-in repair-copilot">
    <section className="repair-intro">
      <div className="repair-orbit" aria-hidden="true"><span>✳</span></div>
      <div><span className="panel-kicker">HUMAN-APPROVED DATA CARE</span><h2>Your data, repaired with you in control.</h2><p>The copilot looks for clear, explainable fixes. Review every affected field, preview the exact impact, then approve a separate corrected download.</p></div>
      <div className="repair-flow"><span>01 <b>Suggest</b></span><i>→</i><span>02 <b>Preview</b></span><i>→</i><span>03 <b>Approve</b></span></div>
    </section>
    {!isCsv ? <section className="panel"><EmptyState title="CSV repair is ready first" body="Analysis supports CSV, XLSX, and XLS. The first repair workflow supports CSV so workbook sheets, formulas, and formatting are never silently flattened." /></section> : <>
      <section className="panel repair-controls">
        <div><span className="panel-kicker">OPTIONAL AI EXPLANATIONS</span><h3>Choose how suggestions are generated</h3><p>Deterministic checks find the candidate repairs. When enabled, Groq only ranks and explains them; it cannot create or apply edits.</p></div>
        <label className="groq-consent"><input type="checkbox" checked={useGroq} onChange={(event) => setUseGroq(event.target.checked)} /><span><strong>Use Groq for explanations</strong><small>Column names and issue counts only. Cell values and rows stay on this app.</small></span></label>
        <button className="button button-dark" onClick={() => onRequest("propose")} disabled={busy}>{busy ? <><span className="spinner" /> Checking…</> : candidates ? "Refresh suggestions" : "Find repair suggestions"}</button>
      </section>
      {error && <p className="error-message" role="alert">{error}</p>}
      {candidates && <>
        <section className="panel"><div className="panel-head"><div><span className="panel-kicker">{candidates.agent_mode === "groq" ? "GROQ-ASSISTED · SAFE CANDIDATES" : "LOCAL CHECKS · NO AI DATA SHARING"}</span><h2>Review suggested fixes</h2></div><span className="panel-meta">{candidates.candidates.length} CANDIDATES</span></div>
          <p className="repair-privacy">{candidates.privacy}</p>
          {!candidates.candidates.length ? <EmptyState title="No clear repairs found" body="The current checks found no whitespace, missing-value, or exact-duplicate issues to propose." /> : <div className="repair-list">{candidates.candidates.map((candidate) => <label className={`repair-option ${selected.includes(candidate.id) ? "selected" : ""}`} key={candidate.id}>
            <input type="checkbox" checked={selected.includes(candidate.id)} onChange={() => toggle(candidate.id)} />
            <span className="repair-option-content"><span className="repair-option-title"><strong>{candidate.kind === "trim_text" ? "Trim surrounding whitespace" : candidate.kind === "normalize_whitespace" ? "Normalize repeated whitespace" : candidate.kind === "fill_missing" ? "Fill missing values" : "Remove exact duplicate rows"}</strong><span className="repair-badges">{candidate.recommended && <em className="copilot-pick">COPILOT PICK</em>}<em>{pretty(candidate.affected_rows)} {candidate.kind === "drop_duplicates" ? "rows removed" : "cells changed"}</em></span></span>
              {candidate.column && <span className="repair-column">{candidate.column}</span>}
              <span className="repair-rationale">{candidate.rationale}</span>
              <span className="repair-caution">{candidate.caution}</span>
              {!!candidate.examples?.length && <span className="repair-examples">{candidate.examples.map((example, index) => <span key={index}><code>{example.before ?? "(blank)"}</code><b>→</b><code>{example.after}</code></span>)}</span>}
            </span>
          </label>)}</div>}
        </section>
        {!!candidates.candidates.length && <div className="repair-actions"><span>{selected.length} selected · Nothing changes until you approve a preview.</span><button className="button button-dark" onClick={() => onRequest("preview")} disabled={busy || !selected.length}>{busy ? "Building preview…" : "Preview selected fixes"}<span aria-hidden="true"> →</span></button></div>}
      </>}
      {preview && <section className="panel repair-preview"><div className="panel-head"><div><span className="panel-kicker">PREVIEW ONLY · ORIGINAL FILE UNCHANGED</span><h2>Here’s exactly what would change</h2></div><span className="row-impact">{pretty(preview.rows_before)} <i>→</i> {pretty(preview.rows_after)} <small>ROWS</small></span></div>
        <div className="preview-operations">{preview.operations.map((operation) => <article key={operation.id}><span className="preview-check">✓</span><div><strong>{operation.kind === "trim_text" ? "Whitespace cleanup" : operation.kind === "normalize_whitespace" ? "Normalize repeated whitespace" : operation.kind === "fill_missing" ? "Missing values" : "Exact duplicates"}{operation.column ? ` · ${operation.column}` : ""}</strong><p>{operation.strategy}</p><small>{pretty(operation.affected_rows)} affected {operation.kind === "drop_duplicates" ? "rows" : "cells"}{operation.kind === "fill_missing" ? ` · replacement: ${String(operation.fill_value)}` : ""}</small></div></article>)}</div>
        <div className="approval-note"><span>↳</span><p>Approving downloads a new <strong>_repaired.csv</strong> copy. Your uploaded original stays unchanged, so you can discard the repaired copy to undo.</p></div>
        <button className="button button-dark approve-repairs" onClick={() => onRequest("apply")} disabled={busy}>{busy ? "Preparing repaired copy…" : "Approve & download repaired copy"}</button>
        {download && <p className="repair-success" role="status">Your repaired copy was downloaded as <strong>{download}</strong>. The original is unchanged.</p>}
      </section>}
    </>}
  </div>;
}

function Audit({ report, onDownload }) {
  const entries = [
    ...report.quality_report.dimensions.map((item) => ({ name: `Quality · ${item.name}`, evidence: item.evidence })),
    ...(report.statistics ?? []).map((item) => ({ name: `Statistics · ${item.column}`, evidence: item.evidence })),
    ...(report.correlations ?? []).map((item) => ({ name: `Correlation · ${item.col_a} × ${item.col_b}`, evidence: item.evidence })),
  ];
  return <div className="content-stack animate-in">
    <section className="audit-heading panel"><div><span className="panel-kicker">PROVENANCE</span><h2>A number should come with its working.</h2><p>This ledger pairs computed results with their source tool, formula, input size, dataset fingerprint, and confidence.</p></div><button className="button button-dark" onClick={onDownload}>Download JSON ledger</button></section>
    <section className="panel"><PanelHead kicker="TRACEABLE METRICS" title="Evidence records" meta={`${entries.length} RECORDS`} /><div className="ledger-list">{entries.map((entry) => <details key={entry.name} className="ledger-row"><summary><span className="ledger-dot" /><strong>{entry.name}</strong><span className="ledger-source">{entry.evidence.source_tool.split(".").at(-1)}</span><span className="ledger-open">＋</span></summary><div className="ledger-body"><code>{entry.evidence.calculation}</code><EvidenceGrid evidence={entry.evidence} /></div></details>)}</div></section>
  </div>;
}

function downloadCsv(name, headers, rows) {
  const quote = (v) => `"${String(v ?? "").replaceAll('"', '""')}"`;
  const blob = new Blob([[headers, ...rows].map(row => row.map(quote).join(",")).join("\r\n")], {type:"text/csv;charset=utf-8"});
  const url = URL.createObjectURL(blob); const link = document.createElement("a");
  link.href=url; link.download=name; link.click(); setTimeout(()=>URL.revokeObjectURL(url),1000);
}

function DistributionChart({name, profile}) {
  if (!profile?.counts?.length) return null;
  const max=Math.max(...profile.counts,1), n=profile.counts.length;
  const box=profile.box??[];
  return <article className="chart-card"><h3>{name}</h3><svg viewBox="0 0 420 170" role="img" aria-label={`Histogram for ${name}`}><line x1="28" y1="142" x2="408" y2="142" stroke="#cbd5e1"/>{profile.counts.map((v,i)=>{const w=350/n;return <rect key={i} x={34+i*w} y={135-v/max*105} width={Math.max(2,w-3)} height={v/max*105} rx="3" fill="#4d7cff"><title>{profile.edges[i]}–{profile.edges[i+1]}: {v}</title></rect>})}<text x="28" y="160">{pretty(profile.edges[0])}</text><text x="360" y="160">{pretty(profile.edges.at(-1))}</text><text x="28" y="20">Count</text></svg>{box.length===5&&<div className="box-summary"><span>MIN {pretty(box[0])}</span><span>Q1 {pretty(box[1])}</span><strong>MEDIAN {pretty(box[2])}</strong><span>Q3 {pretty(box[3])}</span><span>MAX {pretty(box[4])}</span></div>}<button className="text-button" onClick={()=>downloadCsv(`${name}-distribution.csv`,["bin_start","bin_end","count"],profile.counts.map((v,i)=>[profile.edges[i],profile.edges[i+1],v]))}>Export chart data</button></article>;
}
function CategoryChart({name,data}) { const max=Math.max(...data.map(x=>x.count),1); return <article className="chart-card"><h3>{name}</h3><div className="category-bars">{data.map(item=><div key={item.label} title={`${item.label}: ${item.count}`}><span>{item.label}</span><i><b style={{width:`${item.count/max*100}%`}}/></i><strong>{pretty(item.count)}</strong></div>)}</div><button className="text-button" onClick={()=>downloadCsv(`${name}-categories.csv`,["value","count"],data.map(x=>[x.label,x.count]))}>Export chart data</button></article>; }
function CorrelationHeatmap({correlations}) {
  const names=[...new Set(correlations.flatMap(x=>[x.col_a,x.col_b]))];
  const get=(a,b)=>a===b?1:(correlations.find(x=>(x.col_a===a&&x.col_b===b)||(x.col_a===b&&x.col_b===a))?.coefficient??0);
  return <div className="heatmap-wrap"><table className="heatmap"><thead><tr><th></th>{names.map(n=><th key={n}>{n}</th>)}</tr></thead><tbody>{names.map(a=><tr key={a}><th>{a}</th>{names.map(b=>{const v=get(a,b);return <td key={b} style={{background:v>=0?`rgba(0,82,255,${Math.abs(v)*.75})`:`rgba(190,96,69,${Math.abs(v)*.75})`,color:Math.abs(v)>.48?"white":"#172033"}} title={`${a} × ${b}: ${v.toFixed(3)}`}>{v.toFixed(2)}</td>})}</tr>)}</tbody></table></div>;
}
function ScatterChart({pair}) {
  const xs=pair.points.map(p=>p[0]),ys=pair.points.map(p=>p[1]);if(!xs.length)return null;
  const xmin=Math.min(...xs),xmax=Math.max(...xs),ymin=Math.min(...ys),ymax=Math.max(...ys);
  return <article className="chart-card"><h3>{pair.x} × {pair.y}</h3><svg viewBox="0 0 420 230" role="img" aria-label={`Scatter plot of ${pair.x} and ${pair.y}`}><line x1="36" y1="190" x2="405" y2="190" stroke="#cbd5e1"/><line x1="36" y1="20" x2="36" y2="190" stroke="#cbd5e1"/>{pair.points.map((p,i)=><circle key={i} cx={40+(p[0]-xmin)/(xmax-xmin||1)*350} cy={186-(p[1]-ymin)/(ymax-ymin||1)*155} r="3" fill="#0052ff" opacity=".55"><title>{pair.x}: {pretty(p[0])}; {pair.y}: {pretty(p[1])}</title></circle>)}<text x="38" y="215">{pretty(xmin)}</text><text x="344" y="215">{pretty(xmax)}</text></svg><button className="text-button" onClick={()=>downloadCsv(`${pair.x}-${pair.y}-scatter.csv`,[pair.x,pair.y],pair.points)}>Export plotted data</button></article>;
}
function MissingnessMap({data}) {
 if(!data?.columns?.length||!data?.rows?.length)return <EmptyState title="No missing values to map" body="No rows were sampled or no columns are available."/>;
 return <div className="missing-map-wrap"><div className="missing-map" style={{gridTemplateColumns:`repeat(${data.columns.length}, minmax(12px,1fr))`}}>{data.rows.flatMap((row,r)=>row.missing.map((missing,c)=><span key={r+"-"+c} className={missing?"is-missing":""} title={`Sampled row ${row.index+1} · ${data.columns[c]} · ${missing?"missing":"present"}`}/>))}</div><div className="missing-map-labels">{data.columns.map(c=><span key={c} title={c}>{c}</span>)}</div><div className="map-legend"><i/> Present <i className="is-missing"/> Missing</div></div>;
}
function Explorer({report,filter,setFilter,sortBy,setSortBy}) {
  const profiles=report.quality_report.column_profiles??[];
  const filtered=profiles.filter(x=>x.column_name.toLowerCase().includes(filter.toLowerCase())).sort((a,b)=>sortBy==="unique"?b.n_unique-a.n_unique:sortBy==="name"?a.column_name.localeCompare(b.column_name):b.pct_missing-a.pct_missing);
  const dates=report.visual_profile?.dates??{};
  const dateCharts=Object.entries(dates);
  return <div className="content-stack animate-in">
    <section className="panel"><PanelHead kicker="COMPLETENESS PATTERN" title="Missingness map" meta="SAMPLED ROWS × FIELDS"/><MissingnessMap data={report.visual_profile?.missingness}/><p className="small-note">Each mark represents a sampled row and field. Blue means present; orange means missing. Column profiles show exact counts.</p></section>
    <section className="panel"><PanelHead kicker="FIELD EXPLORER" title="Find and inspect columns" meta={`${profiles.length} FIELDS`}/><div className="explorer-controls"><input aria-label="Search columns" placeholder="Search columns…" value={filter} onChange={e=>setFilter(e.target.value)}/><label>Sort by <select value={sortBy} onChange={e=>setSortBy(e.target.value)}><option value="missing">Missing values</option><option value="unique">Unique values</option><option value="name">Name</option></select></label><button className="button button-dark button-small" onClick={()=>downloadCsv("datapilot-column-profile.csv",["column","type","missing_count","missing_percent","unique_count","unique_percent"],filtered.map(x=>[x.column_name,x.dtype,x.n_missing,x.pct_missing,x.n_unique,x.pct_unique]))}>Export fields</button></div>
    <div className="explorer-grid">{filtered.map(x=><article className="field-card" key={x.column_name}><div><strong>{x.column_name}</strong><span className="type-tag">{x.dtype}</span></div><div className="field-stats"><span>Missing <b>{x.pct_missing}%</b></span><span>Unique <b>{pretty(x.n_unique)}</b></span><span>Rows <b>{pretty(report.dataset.n_rows)}</b></span></div><div className="missing-bar"><i style={{width:`${x.pct_missing}%`}}/></div><small>{x.n_missing} missing · {x.pct_unique}% unique</small></article>)}</div></section>
    {dateCharts.map(([column,info])=><section className="panel" key={column}><PanelHead kicker="TIME SERIES · MONTHLY" title={column}/><div className="chart-grid">{(Object.keys(info.metrics??{}).length?Object.entries(info.metrics):[["Row count",info.count??[]]]).map(([metric,points])=><article className="chart-card" key={metric}><h3>{metric}</h3><svg viewBox="0 0 600 190" role="img" aria-label={`${metric} by month`}>{linePath(points,600,165,25,25)}<text x="25" y="184">{points[0]?.label}</text><text x="500" y="184">{points.at(-1)?.label}</text></svg><button className="text-button" onClick={()=>downloadCsv(`${column}-${metric}-monthly.csv`,["month",metric],points.map(p=>[p.label,p.value]))}>Export chart data</button></article>)}</div></section>)}
  </div>;
}
function linePath(points,w,h,padX,padY){if(!points?.length)return null;const vals=points.map(x=>x.value),lo=Math.min(...vals),hi=Math.max(...vals),span=hi-lo||1;const coords=points.map((p,i)=>[padX+i*(w-padX*2)/Math.max(points.length-1,1),h-padY-(p.value-lo)/span*(h-padY*2)]);return <g><polyline fill="none" stroke="#0052ff" strokeWidth="3" points={coords.map(p=>p.join(",")).join(" ")}/>{coords.map((p,i)=><circle key={i} cx={p[0]} cy={p[1]} r="3" fill="#0052ff"><title>{points[i].label}: {pretty(points[i].value)}</title></circle>)}</g>}
function Compare({report,previous,previousFilename}) {
  if(!previous)return <section className="panel"><PanelHead kicker="RUN COMPARISON" title="Compare dataset analyses"/><EmptyState title="Analyze another file to compare" body="DataPilot keeps the previous analysis in this session. Upload a newer or revised dataset and this view will compare row counts, schema, quality dimensions, and anomaly counts."/></section>;
  const now=report.quality_report,old=previous.quality_report;
  const metrics=[["Rows",previous.dataset.n_rows,report.dataset.n_rows],["Columns",previous.dataset.n_cols,report.dataset.n_cols],["Quality score",old.composite_score,now.composite_score],...old.dimensions.map(d=>[d.name,d.score,now.dimensions.find(n=>n.name===d.name)?.score??0]),...previous.anomalies.map(a=>[`${a.method} flags`,a.n_flagged,report.anomalies.find(n=>n.method===a.method)?.n_flagged??0])];
  const oldCols=new Set(previous.quality_report.column_profiles.map(x=>x.column_name)),newCols=new Set(report.quality_report.column_profiles.map(x=>x.column_name));
  const added=[...newCols].filter(x=>!oldCols.has(x)),removed=[...oldCols].filter(x=>!newCols.has(x));
  return <div className="content-stack animate-in"><section className="panel"><PanelHead kicker="RUN COMPARISON" title="What changed?" meta="CURRENT SESSION"/><div className="compare-files"><span>{previousFilename||previous.dataset.filename}</span><b>→</b><span>{report.dataset.filename}</span></div><div className="table-wrap"><table><thead><tr><th>METRIC</th><th>PREVIOUS</th><th>CURRENT</th><th>CHANGE</th></tr></thead><tbody>{metrics.map(([label,a,b])=><tr key={label}><td className="field-name">{label}</td><td>{pretty(a)}</td><td>{pretty(b)}</td><td className={Number(b)-Number(a)<0?"text-low":"text-good"}>{Number.isFinite(Number(b)-Number(a))?(Number(b)-Number(a)>0?"+":"")+pretty(Number(b)-Number(a)):"—"}</td></tr>)}</tbody></table></div><div className="schema-diff"><h3>Schema changes</h3><p><strong>Added:</strong> {added.join(", ")||"None"}</p><p><strong>Removed:</strong> {removed.join(", ")||"None"}</p></div><p className="small-note">This compares analysis summaries. It does not assert that the two datasets contain matching records.</p></section></div>;
}
function PrintReport({report}) {
 const profiles=report.quality_report.column_profiles??[], visual=report.visual_profile??{};
 return <article><header><h1>DataPilot analysis report</h1><p>{report.dataset.filename} · {pretty(report.dataset.n_rows)} rows · {report.dataset.n_cols} columns</p><p>Dataset fingerprint: {report.dataset.dataset_version}</p></header>
 <h2>Executive summary</h2><p>Quality score: <strong>{report.quality_report.composite_score}/100</strong>. {report.insight.summary}</p>
 <h2>Quality dimensions</h2><table><thead><tr><th>Dimension</th><th>Score</th><th>Finding</th></tr></thead><tbody>{report.quality_report.dimensions.map(d=><tr key={d.name}><td>{d.name}</td><td>{d.score}</td><td>{d.reason}</td></tr>)}</tbody></table>
 <h2>Column profile</h2><table><thead><tr><th>Field</th><th>Type</th><th>Missing</th><th>Unique</th></tr></thead><tbody>{profiles.map(c=><tr key={c.column_name}><td>{c.column_name}</td><td>{c.dtype}</td><td>{c.pct_missing}%</td><td>{c.n_unique}</td></tr>)}</tbody></table>
 <h2>Numeric distributions</h2><div className="chart-grid">{Object.entries(visual.distributions??{}).map(([name,p])=><DistributionChart key={name} name={name} profile={p}/>)}</div>
 <h2>Numeric relationships</h2><div className="chart-grid">{(visual.scatter??[]).slice(0,12).map(pair=><ScatterChart key={pair.x+pair.y} pair={pair}/>)}</div>
 <h2>Completeness pattern</h2><MissingnessMap data={visual.missingness}/>
 <h2>Trends over time</h2>{Object.entries(visual.dates??{}).map(([column,info])=><div key={column}><h3>{column}</h3><div className="chart-grid">{(Object.keys(info.metrics??{}).length?Object.entries(info.metrics):[["Row count",info.count??[]]]).map(([metric,points])=><article className="chart-card" key={metric}><h3>{metric}</h3><svg viewBox="0 0 600 190">{linePath(points,600,165,25,25)}</svg></article>)}</div></div>)}
 <h2>Relationships</h2><CorrelationHeatmap correlations={report.correlations??[]}/>
 <h2>Most common categories</h2><div className="chart-grid">{Object.entries(visual.categories??{}).map(([name,data])=><CategoryChart key={name} name={name} data={data}/>)}</div>
 <h2>Flagged observations</h2><table><thead><tr><th>Detector</th><th>Row</th><th>Field</th><th>Value</th><th>Score</th></tr></thead><tbody>{(report.anomalies??[]).flatMap(a=>(a.results??[]).map((r,i)=><tr key={a.method+r.column+r.row_index+i}><td>{a.method}</td><td>{r.row_index+1}</td><td>{r.column}</td><td>{pretty(r.value)}</td><td>{pretty(r.score)}</td></tr>))}</tbody></table>
 <h2>Evidence and method</h2><p>{(report.quality_report.dimensions??[]).map(d=>`${d.name}: ${d.evidence.calculation}`).join(" · ")}</p><footer>Generated by DataPilot · deterministic profile · {new Date().toLocaleString()}</footer></article>;
}

function Metric({ label, value, note, accent = "" }) { return <section className="metric-card"><span>{label}</span><strong className={accent}>{value}</strong><small>{note}</small></section>; }
function PanelHead({ kicker, title, meta }) { return <div className="panel-head"><div><span className="panel-kicker">{kicker}</span><h2>{title}</h2></div>{meta && <span className="panel-meta">{meta}</span>}</div>; }
function EvidenceGrid({ evidence }) { return <div className="evidence-grid"><span>TOOL<strong>{evidence.source_tool}</strong></span><span>ROWS<strong>{pretty(evidence.rows_used)}</strong></span><span>CONFIDENCE<strong>{pretty(evidence.confidence)}</strong></span><span>DATASET HASH<strong className="hash-short">{evidence.dataset_version}</strong></span></div>; }
function EmptyState({ title, body }) { return <div className="empty-state"><h3>{title}</h3><p>{body}</p></div>; }

createRoot(document.getElementById("root")).render(<React.StrictMode><App /></React.StrictMode>);
