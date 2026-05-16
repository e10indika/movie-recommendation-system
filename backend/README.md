# Backend — Movie Recommendation API

FastAPI + PySpark ALS recommendation backend running on port **8003**.

## Setup

```bash
cd backend
pip install -r requirements.txt
```

## Train the model (run once)

```bash
# From project root, after downloading MovieLens data:
python3 backend/train_and_save.py
```

## Run the API

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8003
```

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/health` | Health + model status |
| `GET` | `/api/v1/users` | List of available user IDs |
| `GET` | `/api/v1/movies` | Movie catalogue (top 100) |
| `GET` | `/api/v1/recommend/{user_id}?n=10` | Top-N recommendations |

Interactive docs: http://localhost:8003/docs
