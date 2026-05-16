# Data Directory

This directory stores the MovieLens dataset required to train the recommendation model.

## Download MovieLens Small (100K ratings)

```bash
cd data
bash download_movielens.sh
```

This downloads **ml-latest-small** (~3 MB) from GroupLens and extracts:

| File | Description |
|------|-------------|
| `ml-latest-small/ratings.csv` | 100,836 ratings from 610 users across 9,742 movies |
| `ml-latest-small/movies.csv` | Movie titles and genres |
| `ml-latest-small/tags.csv` | User-applied tags |
| `ml-latest-small/links.csv` | IMDb / TMDB links |

## Alternative: Manual Download

https://grouplens.org/datasets/movielens/latest/

Place `ratings.csv` and `movies.csv` directly in this `data/` directory OR inside `data/ml-latest-small/`. The training script checks both locations.

## Notes

- Model/data files are excluded from git (see `.gitignore`)
- After downloading, run `python3 backend/train_and_save.py` from the project root
