# Scaler Program Evaluator

A tool for counselors. For a lead it maps the persona, looks up how similar past learners fared in the refund funnel, and shows a recommended program, a fallback program and a confidence score.

## What it does

- **Single lookup:** search a lead by email, phone or name. The lead is fetched live from Metabase and evaluated.
- **Bulk upload (two modes):** upload a CSV or XLSX with full lead data, or a file with only an `email` column. In the second case the lead details are looked up in Metabase.
- **Persona mapping:** a role is mapped to one of nine personas by `src/role_taxonomy.py`. When the role is missing, company type and program interest are used and the persona is marked as inferred.
- **Program choice:** a learned model (`src/learned_recommender.py`) estimates which programs the lead is likely to take, using the lead's Metabase record. Among the realistic ones it puts the program with the lowest refund rate first, and the next best is the fallback. The eligibility rules still apply. The card shows the refund history behind the choice: the program's overall refund rate, the 40 most similar past learners (`src/cohort_matcher.py`) and the batch level.
- **Honest inputs:** missing education is inferred from work history where possible, and anything assumed or inferred is labelled on the card.

## Tech stack

Python 3.11, FastAPI, Uvicorn, Pandas. The front end is one HTML page with no build step. SQLite (WAL mode) stores uploaded leads.

## Run locally

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # then fill in the Metabase values
set -a && source .env && set +a
python run_app.py
```

Open `http://localhost:8000`.

## Deploy on Railway

1. Push the repository to GitHub (see below).
2. In Railway choose **New Project, Deploy from GitHub repo** and select it. Railway reads `railway.json` and builds the `Dockerfile`.
3. Open the service's **Variables** tab and add the values from the table below. Never put them in the repository.
4. Under **Settings, Networking** generate a public domain. The health check is `/health`.
5. Optional: add a **Volume** mounted at `/data` and set `DATABASE_PATH=/data/leads_store.db` so uploaded leads survive a redeploy.

### Environment variables

| Variable | Required | Notes |
|---|---|---|
| `METABASE_URL` | yes | Base address of your Metabase |
| `METABASE_USERNAME`, `METABASE_PASSWORD` | yes, unless an API key is used | A service account is best |
| `METABASE_API_KEY` | alternative | Used instead of username and password |
| `METABASE_CARD_ID` | no | Defaults to the lead card |
| `METABASE_EMAIL_PARAM_ID` | no | Defaults to the card's email parameter |
| `METABASE_TIMEOUT` | no | Seconds, default 30 (lookups wait up to 90) |
| `DATABASE_PATH` | no | Path of the SQLite file, for a volume |
| `WORKERS` | no | Default 1. Keep low on small plans |
| `ENABLE_BULK_INGEST` | no | Default off. Loads every Metabase batch into SQLite, which needs a lot of disk and time |
| `COHORT_MATCH_K` | no | Default 40 |
| `PORT` | set by Railway | Do not set it yourself |

## Push to GitHub

```bash
git status                  # check that no secret or data file is listed
git add .
git commit -m "Prepare for Railway deployment"
git push origin main
```

## Security

- Secrets are read from environment variables. `.env` and `metabase_config.json` are git-ignored and excluded from the Docker image.
- `Database/` (learner emails and sales names), spreadsheets, databases and CSV files are git-ignored. Only two precomputed, anonymous CSV files in `output/` are tracked, because the app reads them at run time.
- If a credential was ever committed, treat it as exposed: change it in Metabase, because deleting the file does not remove it from git history.

## Refreshing the refund history

`output/retention_matrix.json`, `output/learner_outcomes.csv` and `output/empirical_persona_matrix.csv` are built from the refund-funnel spreadsheet, which is not stored in the repository. To rebuild them, place the workbook in `Database/` (the pipeline uses the newest of `Refunds Funnel (2).xlsx` or `(1).xlsx`, or the path in `REFUND_FUNNEL_PATH`). Only its `Raw` sheet is read. Then run:

```bash
python -m src.clean_matrix_pipeline
```

Keeping the recommendation honest, every month:

```bash
python tools/monthly_refresh.py       # the whole monthly routine in the right order: review, rebuild matrix, retrain, rebuild the review workbook
python tools/monthly_review.py         # was the program sold the tool's primary or fallback, and how many refunded in each group
                                       # (the review and the training use each lead as seen on arrival, src/arrival_view.py, not the record created at the sale)
python tools/build_review_workbook.py # live Excel review of the last 3 cohorts: refund rate as sold vs if the tool's primary had been sold, by team, program, persona and more
python tools/train_recommender.py     # retrain the learned ranking when the match share falls or the refund gap closes
python tools/honest_backtest.py       # accuracy on months the model never saw (trains a model only on earlier cohorts; the live model is not touched)
```

Which accuracy to quote: the review workbook's first sheets use months the model was trained on, so they read higher than new leads will get. The "Held-Out Accuracy" sheet (from `honest_backtest.py`) is the figure to expect on new leads. It also shows that following the tool's recommendation does not yet reduce refunds reliably: the tool shows the programs a lead is likely to take, with each program's refund record beside them.

The tools need Metabase access. Install their extra packages with `pip install -r requirements-tools.txt` (adds scikit-learn, which the app itself does not need).

## Project structure

```
.
├── Dockerfile, railway.json      # container and Railway settings
├── docker-entrypoint.sh          # start script (no secrets written to disk)
├── requirements.txt, requirements-tools.txt   # app packages; extra packages for tools/
├── run_app.py                    # launcher (reads PORT)
├── .env.example                  # variable names only, no values
├── src/
│   ├── server.py                 # FastAPI app and routes
│   ├── evaluator.py              # evaluation, ranking, confidence, card text
│   ├── role_taxonomy.py          # role to persona mapping
│   ├── learned_recommender.py    # which programs a lead will take, ranked with refund rates
│   ├── cohort_matcher.py         # nearest past learners and observed refunds
│   ├── matrix_engine.py          # refund matrix and persona helpers
│   ├── clean_matrix_pipeline.py  # rebuilds the matrix from the spreadsheet
│   ├── batch_processor.py        # bulk upload processing
│   ├── metabase_client.py        # Metabase queries
│   ├── lead_store.py             # SQLite storage
│   └── mb_ingest.py              # optional bulk loader
├── web/index.html                # counselor desk
└── output/                       # precomputed refund history (the SQLite file lives here too, git-ignored)
```
