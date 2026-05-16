# Frontend — Movie Recommendation UI

React + Vite frontend running on port **5174**.

## Setup & Run

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5174

## Structure

```
src/
├── components/
│   ├── MovieCard.jsx          # Individual movie card with stars + genre pills
│   ├── UserSelector.jsx       # Dropdown + manual user ID input
│   ├── RecommendationList.jsx # Grid of movie cards
│   └── LoadingSpinner.jsx     # CSS spinner
├── services/
│   └── api.js                 # Axios client → http://localhost:8003
├── App.jsx                    # Root component
└── App.css                    # Dark theme styles
```
