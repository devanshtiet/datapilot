# DataPilot

DataPilot profiles CSV and Excel datasets with a React dashboard and a FastAPI analysis service. Every metric is computed deterministically and returned with its evidence; uploaded rows are not sent to an AI provider.

## Stack

- **Frontend:** React 19, Vite
- **Backend:** FastAPI, Pandas, NumPy
- **Analysis:** quality scoring, descriptive statistics, correlations, IQR and Z-score anomaly detection

## Run locally

Requirements: Python 3.11+ and Node.js 20+.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements-local.txt
pnpm install
```

Start the API and frontend in separate terminals:

```bash
python -m uvicorn api.index:app --reload --port 8000
```

```bash
pnpm dev
```

Open `http://localhost:3000`. The Vite development server proxies `/api` requests to FastAPI on port 8000. You can load the included retail-orders sample or upload your own CSV, XLS, or XLSX file.

## DataPilot intro

Watch the [8-second DataPilot intro](https://devanshtiet.github.io/datapilot/) or download [the MP4](docs/assets/datapilot-intro.mp4). The GitHub Pages site includes the original upbeat music cue and a short overview of the product.

To edit the Remotion composition locally:

```bash
pnpm video:studio
```

The preview opens at `http://localhost:3001`. Render the MP4 and page poster with `pnpm video:render` and `pnpm video:poster`.

The **Repair Copilot** currently offers previewable CSV fixes for surrounding whitespace, missing values, and exact duplicate rows. Suggestions are computed locally. If the user opts in to Groq explanations, only column names and issue counts are sent; the model cannot invent or apply operations. Preview is computed by deterministic code, and approval downloads a separate repaired copy while leaving the original upload unchanged. XLS/XLSX repair is deliberately not offered yet to avoid flattening workbook sheets, formulas, or formatting.

## Production build

```bash
pnpm build
```

The Vite build is written to `frontend/dist`. FastAPI serves those assets from `/` and exposes the analysis API under `/api`. Vercel builds the React bundle and deploys the FastAPI application from `api/index.py`.

## API

- `GET /api/health` — deployment health check
- `GET /api/docs` — interactive API reference
- `POST /api/profile?filename=retail_orders_demo.csv` — profile raw CSV/XLS/XLSX bytes
- `POST /api/repairs/propose?filename=dataset.csv&use_groq=false` — find repair candidates; Groq is opt-in
- `POST /api/repairs/preview?filename=dataset.csv&selected=[...]` — compute an exact preview from the original CSV
- `POST /api/repairs/apply?filename=dataset.csv&selected=[...]` — create a separate repaired CSV after explicit UI approval

Uploads are limited to 4 MB on Vercel. Example:

```bash
curl --data-binary "@scripts/sample_data/retail_orders_demo.csv" \
  -H "Content-Type: application/octet-stream" \
  "https://<your-vercel-domain>/api/profile?filename=retail_orders_demo.csv"
```

## Project layout

```text
api/index.py            Vercel FastAPI entry point
app/api/main.py         API routes and React static-file mount
app/analytics/           Statistics and correlation analysis
app/anomaly/             IQR and Z-score detectors
app/data/                File ingestion and quality scoring
frontend/src/             React dashboard
frontend/public/          Bundled demo dataset
scripts/sample_data/      Sample datasets
```
