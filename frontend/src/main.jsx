import React, { useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

const sections = [
  ["overview", "Overview", "01"],
  ["quality", "Quality profile", "02"],
  ["statistics", "Statistics", "03"],
  ["anomalies", "Anomalies", "04"],
  ["insight", "Agent notes", "05"],
  ["repairs", "Repair copilot", "06"],
  ["audit", "Evidence ledger", "07"],
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
  const totalFlagged = anomalies.reduce((sum, row) => sum + row.n_flagged, 0);
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
            {report && <button className="button button-dark button-small" onClick={() => inputRef.current?.click()}>Analyze another file</button>}
          </div>
          <input ref={inputRef} className="visually-hidden" type="file" accept=".csv,.xlsx,.xls" onChange={(event) => analyze(event.target.files?.[0])} />
        </header>

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
            <div className="privacy-note"><span className="lock-glyph" aria-hidden="true">⌑</span> Files are analyzed for this request; raw rows are not sent to an AI provider.</div>
          </section>
        ) : (
          <>
            <section className="page-heading">
              <div><div className="eyebrow left"><span className="eyebrow-line" /> DATASET REVIEW</div><h1>{sections.find(([id]) => id === section)?.[1] ?? "Overview"}</h1><p>{filename} <span className="heading-dot">·</span> {pretty(report.dataset.n_rows)} rows <span className="heading-dot">·</span> {report.dataset.n_cols} columns</p></div>
              <div className={`score-chip ${scoreClass}`}><span className="score-chip-label">OVERALL QUALITY</span><strong>{score.toFixed(1)}<small> / 100</small></strong></div>
            </section>
            {section === "overview" && <Overview report={report} scoreClass={scoreClass} totalFlagged={totalFlagged} onNavigate={setSection} />}
            {section === "quality" && <Quality report={report} scoreClass={scoreClass} />}
            {section === "statistics" && <Statistics stats={stats} correlations={correlations} selected={selectedStat} setSelected={setSelectedStat} evidence={selectedStatEvidence} />}
            {section === "anomalies" && <Anomalies anomalies={anomalies} totalFlagged={totalFlagged} />}
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

function Statistics({ stats, correlations, selected, setSelected, evidence }) {
  return <div className="content-stack animate-in">
    <section className="panel"><PanelHead kicker="NUMERIC PROFILE" title="Descriptive statistics" meta={`${stats.length} NUMERIC FIELDS`} />
      {!stats.length ? <EmptyState title="No numeric fields found" body="This dataset has no columns that can be summarized as numbers." /> : <><div className="table-wrap"><table className="wide-table"><thead><tr><th>FIELD</th><th>VALID</th><th>MEAN</th><th>MEDIAN</th><th>STD. DEV.</th><th>MIN</th><th>MAX</th></tr></thead><tbody>{stats.map((row, index) => <tr key={row.column} className={selected === index ? "selected-row" : ""} onClick={() => setSelected(index)}><td className="field-name">{row.column}</td><td>{pretty(row.n_valid)}</td><td>{pretty(row.mean)}</td><td>{pretty(row.median)}</td><td>{pretty(row.std)}</td><td>{pretty(row.min_val)}</td><td>{pretty(row.max_val)}</td></tr>)}</tbody></table></div>
      {evidence && <div className="selected-evidence"><div><span className="panel-kicker">SELECTED FIELD</span><h3>{stats[selected].column}</h3></div><code>{evidence.calculation}</code><EvidenceGrid evidence={evidence} /></div>}</>}
    </section>
    <section className="panel"><PanelHead kicker="RELATIONSHIPS" title="Pearson correlations" meta={`${correlations.length} PAIRS`} />{correlations.length ? <div className="table-wrap"><table><thead><tr><th>FIELD A</th><th>FIELD B</th><th>PEARSON r</th><th>CONFIDENCE</th></tr></thead><tbody>{correlations.map((item) => <tr key={`${item.col_a}-${item.col_b}`}><td>{item.col_a}</td><td>{item.col_b}</td><td className="mono">{item.coefficient.toFixed(3)}</td><td>{pretty(item.evidence.confidence)}</td></tr>)}</tbody></table></div> : <EmptyState title="No field pairs to compare" body="Pearson correlation appears when the dataset has at least two numeric fields." />}</section>
  </div>;
}

function Anomalies({ anomalies, totalFlagged }) {
  return <div className="content-stack animate-in">
    <section className="anomaly-banner"><div><span className="panel-kicker">DETECTION SUMMARY</span><h2>{totalFlagged ? `${pretty(totalFlagged)} flagged observations` : "No unusual values surfaced"}</h2><p>Two independent univariate detectors scan numeric fields. A flag is a prompt to inspect, not a verdict.</p></div><div className="anomaly-total">{pretty(totalFlagged)}<small>TOTAL FLAGS</small></div></section>
    <div className="anomaly-grid">{anomalies.map((item, index) => <section className="panel detector-card" key={item.method}><span className="card-index">DETECTOR 0{index + 1}</span><div className="detector-heading"><h3>{item.method === "iqr" ? "Interquartile range" : "Z-score"}</h3><strong>{pretty(item.n_flagged)}</strong></div><p>{item.method === "iqr" ? "Flags values beyond Tukey fences around the middle half of the distribution." : "Flags values more than the selected standard-deviation threshold from the mean."}</p><div className="detector-foot"><span>{item.columns_analysed.length} FIELDS SCANNED</span><span>{item.method === "iqr" ? "ROBUST SPREAD" : "STANDARDIZED DISTANCE"}</span></div></section>)}</div>
    <div className="notice-strip"><span className="notice-rule" />This serverless profile runs IQR and Z-score checks. Isolation Forest and hosted agent interpretation remain available in the full local backend workflow.</div>
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
            <span className="repair-option-content"><span className="repair-option-title"><strong>{candidate.kind === "trim_text" ? "Trim surrounding whitespace" : candidate.kind === "fill_missing" ? "Fill missing values" : "Remove exact duplicate rows"}</strong><span className="repair-badges">{candidate.recommended && <em className="copilot-pick">COPILOT PICK</em>}<em>{pretty(candidate.affected_rows)} {candidate.kind === "drop_duplicates" ? "rows removed" : "cells changed"}</em></span></span>
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
        <div className="preview-operations">{preview.operations.map((operation) => <article key={operation.id}><span className="preview-check">✓</span><div><strong>{operation.kind === "trim_text" ? "Whitespace cleanup" : operation.kind === "fill_missing" ? "Missing values" : "Exact duplicates"}{operation.column ? ` · ${operation.column}` : ""}</strong><p>{operation.strategy}</p><small>{pretty(operation.affected_rows)} affected {operation.kind === "drop_duplicates" ? "rows" : "cells"}{operation.kind === "fill_missing" ? ` · replacement: ${String(operation.fill_value)}` : ""}</small></div></article>)}</div>
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

function Metric({ label, value, note, accent = "" }) { return <section className="metric-card"><span>{label}</span><strong className={accent}>{value}</strong><small>{note}</small></section>; }
function PanelHead({ kicker, title, meta }) { return <div className="panel-head"><div><span className="panel-kicker">{kicker}</span><h2>{title}</h2></div>{meta && <span className="panel-meta">{meta}</span>}</div>; }
function EvidenceGrid({ evidence }) { return <div className="evidence-grid"><span>TOOL<strong>{evidence.source_tool}</strong></span><span>ROWS<strong>{pretty(evidence.rows_used)}</strong></span><span>CONFIDENCE<strong>{pretty(evidence.confidence)}</strong></span><span>DATASET HASH<strong className="hash-short">{evidence.dataset_version}</strong></span></div>; }
function EmptyState({ title, body }) { return <div className="empty-state"><h3>{title}</h3><p>{body}</p></div>; }

createRoot(document.getElementById("root")).render(<React.StrictMode><App /></React.StrictMode>);
