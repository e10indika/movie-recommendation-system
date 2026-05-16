# 🎬 Movie Recommendation System

End-to-end collaborative filtering recommendation system using **Apache Spark MLlib ALS**, a **FastAPI** REST backend, and a **React + Vite** frontend.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                   FRONTEND  (React + Vite : 5174)                │
│   UserSelector ──► RecommendationList ──► MovieCard              │
│              │                                                   │
│              └──── Axios ────► http://localhost:8003             │
└──────────────────────────────────────────────────────────────────┘
                               │ HTTP / JSON
┌──────────────────────────────────────────────────────────────────┐
│                   BACKEND  (FastAPI : 8003)                      │
│                                                                  │
│   /api/v1/health                                                 │
│   /api/v1/users          ──► RecommendationService               │
│   /api/v1/movies                      │                          │
│   /api/v1/recommend/{id}         ALSModelManager                 │
│                                  ├── SparkSession (local[*])     │
│                                  ├── ALSModel (from disk)        │
│                                  └── movies_metadata (pandas)    │
└──────────────────────────────────────────────────────────────────┘
                               │ Spark ML
┌──────────────────────────────────────────────────────────────────┐
│   models/als_model/              ← Trained ALS model             │
│   models/movies_metadata.parquet ← Movie catalogue               │
│   models/sample_users.parquet    ← User IDs for dropdown         │
└──────────────────────────────────────────────────────────────────┘
```

---

## Prerequisites

| Tool | Version | Check |
|------|---------|-------|
| Python | ≥ 3.10 | `python3 --version` |
| Java | ≥ 11 | `java -version` (required by PySpark) |
| Node.js | ≥ 18 | `node --version` |

**Java setup (macOS):**
```bash
brew install openjdk@17
export JAVA_HOME=$(/usr/libexec/java_home -v 17)
```

---

## Installation & Usage

### Step 1 — Download MovieLens Data

```bash
cd data
bash download_movielens.sh
cd ..
```

### Step 2 — Train the ALS Model

```bash
cd backend
pip install -r requirements.txt
python3 train_and_save.py
cd ..
```

Expected output:
```
DATASET STATISTICS
  Total ratings   :    100,836
  Unique users    :        610
  Unique movies   :      9,742
  Training RMSE: 0.6234
  Test RMSE    : 0.8731

ARTEFACTS SAVED
  ALS model     : .../models/als_model
  Movies parquet: .../models/movies_metadata.parquet
  Users parquet : .../models/sample_users.parquet
```

### Step 3 — Start the Backend

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8003
```

Verify:
```bash
curl http://localhost:8003/api/v1/health
```

### Step 4 — Start the Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5174

---

## Quick Start (both services)

```bash
bash run.sh
```

---

## API Reference

| Method | Endpoint | Query Params | Description |
|--------|----------|-------------|-------------|
| `GET` | `/api/v1/health` | — | Health check + model status |
| `GET` | `/api/v1/users` | — | Available user IDs |
| `GET` | `/api/v1/movies` | — | Movie catalogue (top 100) |
| `GET` | `/api/v1/recommend/{user_id}` | `n` (1–50, default 10) | Top-N recommendations |

**Interactive docs:** http://localhost:8003/docs

### Example Response — `/api/v1/recommend/1?n=3`

```json
{
  "user_id": 1,
  "recommendations": [
    {
      "movie_id": 318,
      "title": "Shawshank Redemption, The (1994)",
      "genres": "Crime|Drama",
      "predicted_rating": 4.89
    },
    {
      "movie_id": 858,
      "title": "Godfather, The (1972)",
      "genres": "Crime|Drama",
      "predicted_rating": 4.81
    }
  ],
  "total": 2,
  "model_version": "ALS-v1"
}
```

---

## Project Structure

```
pyspark-recommendation-system/
├── backend/
│   ├── app/
│   │   ├── config.py                    # pydantic-settings config (port 8003)
│   │   ├── main.py                      # FastAPI app + lifespan
│   │   ├── routes/
│   │   │   └── recommendation_routes.py # /api/v1 endpoints
│   │   ├── services/
│   │   │   └── recommendation_service.py
│   │   ├── model/
│   │   │   └── als_model.py             # ALSModelManager class
│   │   └── schemas/
│   │       └── recommendation_schema.py # Pydantic models
│   ├── train_and_save.py                # Model training script
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── MovieCard.jsx
│   │   │   ├── UserSelector.jsx
│   │   │   ├── RecommendationList.jsx
│   │   │   └── LoadingSpinner.jsx
│   │   ├── services/api.js              # Axios → localhost:8003
│   │   ├── App.jsx
│   │   └── App.css                      # Dark theme
│   ├── index.html
│   ├── vite.config.js                   # Port 5174
│   └── package.json
├── notebooks/
│   └── exploratory_analysis.ipynb      # EDA + ALS quick test
├── data/
│   ├── download_movielens.sh
│   └── README.md
├── models/                              # Generated artefacts (gitignored)
├── docs/
│   └── architecture.md
├── run.sh                               # Start both services
└── README.md
```

---

## Troubleshooting

**`Model not trained yet`**
→ Run `python3 backend/train_and_save.py` first.

**`JAVA_HOME is not set`**
→ Install Java 11+ and export `JAVA_HOME`.

**`User not found (404)`**
→ User was not in the training set. Try a user from the `/api/v1/users` list.

**Port already in use**
→ Change `PORT` in `backend/app/config.py` and `baseURL` in `frontend/src/services/api.js`.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Recommendation Engine | Apache Spark MLlib — ALS Collaborative Filtering |
| Backend | FastAPI + Uvicorn + Pydantic Settings |
| Frontend | React 18 + Vite + Axios |
| Data Processing | PySpark DataFrames + pandas + PyArrow |
