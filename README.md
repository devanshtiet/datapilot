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

Open `http://localhost:5173`. The Vite development server proxies `/api` requests to FastAPI on port 8000. You can load the included retail-orders sample or upload your own CSV, XLS, or XLSX file.

## Production build

```bash
pnpm build
```

The Vite build is written to `frontend/dist`. FastAPI serves those assets from `/` and exposes the analysis API under `/api`. Vercel builds the React bundle and deploys the FastAPI application from `api/index.py`.

## API

- `GET /api/health` — deployment health check
- `GET /api/docs` — interactive API reference
- `POST /api/profile?filename=retail_orders_demo.csv` — profile raw CSV/XLS/XLSX bytes

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
