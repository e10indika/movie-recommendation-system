/**
 * ColdStartPanel
 *
 * Shown when the recommendation engine detects a cold-start (user not in
 * training data).  Lets the user choose one of four fallback strategies:
 *
 *   1. Popularity    — most popular movies (no input needed)
 *   2. Genre filter  — pick preferred genres
 *   3. Similar movie — enter a movie they like
 *   4. Onboarding    — rate 3-10 seed movies to get personalised picks
 */

import React, { useEffect, useState } from 'react'
import { getByGenre, getMovies, getOnboarding, getPopular, getSimilarTo } from '../services/api'

const ALL_GENRES = [
  'Action', 'Adventure', 'Animation', 'Children', 'Comedy',
  'Crime', 'Documentary', 'Drama', 'Fantasy', 'Film-Noir',
  'Horror', 'Musical', 'Mystery', 'Romance', 'Sci-Fi',
  'Thriller', 'War', 'Western',
]

const SEED_MOVIE_COUNT = 5   // how many movies to show in the onboarding mini-rater

export default function ColdStartPanel({ userId, onResult }) {
  const [strategy, setStrategy]         = useState('popularity')
  const [loading, setLoading]           = useState(false)
  const [error, setError]               = useState(null)

  // Strategy 2 — genres
  const [selectedGenres, setSelectedGenres] = useState([])

  // Strategy 3 — similar-to movie
  const [allMovies, setAllMovies]       = useState([])
  const [seedMovie, setSeedMovie]       = useState('')

  // Strategy 4 — onboarding ratings
  const [seedPool, setSeedPool]         = useState([])   // random selection of movies to rate
  const [ratings, setRatings]           = useState({})   // { movieId: rating }

  // Pre-load movies list for strategies 3 & 4
  useEffect(() => {
    getMovies()
      .then(res => {
        const movies = res.data.movies || []
        setAllMovies(movies)
        // Pick SEED_MOVIE_COUNT random popular movies for onboarding
        const shuffled = [...movies].sort(() => Math.random() - 0.5)
        setSeedPool(shuffled.slice(0, SEED_MOVIE_COUNT))
      })
      .catch(() => {})
  }, [])

  function toggleGenre(genre) {
    setSelectedGenres(prev =>
      prev.includes(genre) ? prev.filter(g => g !== genre) : [...prev, genre]
    )
  }

  async function handleSubmit() {
    setLoading(true)
    setError(null)
    try {
      let res
      if (strategy === 'popularity') {
        res = await getPopular(10)
      } else if (strategy === 'content_based') {
        if (selectedGenres.length === 0) {
          setError('Please select at least one genre.')
          setLoading(false)
          return
        }
        res = await getByGenre(selectedGenres, 10)
      } else if (strategy === 'item_similarity') {
        const id = parseInt(seedMovie, 10)
        if (!id) { setError('Please select a seed movie.'); setLoading(false); return }
        res = await getSimilarTo(id, 10)
      } else if (strategy === 'onboarding') {
        const seedRatings = Object.entries(ratings).map(([mid, r]) => ({
          movie_id: parseInt(mid, 10),
          rating:   parseFloat(r),
        })).filter(r => r.rating > 0)
        if (seedRatings.length < 1) {
          setError('Please rate at least one movie.')
          setLoading(false)
          return
        }
        res = await getOnboarding(seedRatings, 10)
      }
      onResult(res.data)
    } catch (err) {
      setError(err.response?.data?.detail || 'Request failed.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="cold-start-panel">
      <div className="cold-start-header">
        <span className="cold-start-badge">🧊 Cold Start</span>
        <h3>User #{userId} is new — no history found</h3>
        <p>Choose a fallback strategy to get recommendations:</p>
      </div>

      {/* Strategy selector */}
      <div className="strategy-tabs">
        {[
          { id: 'popularity',      label: '🔥 Popular'         },
          { id: 'content_based',   label: '🎭 By Genre'        },
          { id: 'item_similarity', label: '🎬 Similar Movie'   },
          { id: 'onboarding',      label: '⭐ Rate & Discover' },
        ].map(s => (
          <button
            key={s.id}
            className={`strategy-tab ${strategy === s.id ? 'active' : ''}`}
            onClick={() => { setStrategy(s.id); setError(null) }}
          >
            {s.label}
          </button>
        ))}
      </div>

      {/* Strategy-specific inputs */}
      <div className="strategy-body">
        {strategy === 'popularity' && (
          <p className="strategy-desc">Returns the most globally popular movies weighted by rating volume. No input needed.</p>
        )}

        {strategy === 'content_based' && (
          <div>
            <p className="strategy-desc">Select your favourite genres:</p>
            <div className="genre-grid">
              {ALL_GENRES.map(g => (
                <button
                  key={g}
                  className={`genre-chip ${selectedGenres.includes(g) ? 'selected' : ''}`}
                  onClick={() => toggleGenre(g)}
                >
                  {g}
                </button>
              ))}
            </div>
          </div>
        )}

        {strategy === 'item_similarity' && (
          <div>
            <p className="strategy-desc">Pick a movie you like — we'll find similar ones using ALS item factors:</p>
            <select
              className="user-select"
              value={seedMovie}
              onChange={e => setSeedMovie(e.target.value)}
            >
              <option value="">— Choose a movie —</option>
              {allMovies.slice(0, 200).map(m => (
                <option key={m.movieId} value={m.movieId}>{m.title}</option>
              ))}
            </select>
          </div>
        )}

        {strategy === 'onboarding' && (
          <div>
            <p className="strategy-desc">Rate these movies (1–5) to personalise your recommendations:</p>
            <div className="onboarding-grid">
              {seedPool.map(m => (
                <div key={m.movieId} className="onboarding-row">
                  <span className="onboarding-title">{m.title}</span>
                  <div className="star-picker">
                    {[1, 2, 3, 4, 5].map(star => (
                      <button
                        key={star}
                        className={`star-btn ${(ratings[m.movieId] || 0) >= star ? 'lit' : ''}`}
                        onClick={() => setRatings(r => ({ ...r, [m.movieId]: star }))}
                      >
                        ★
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {error && <div className="error-box" style={{ marginBottom: '1rem' }}>⚠️ {error}</div>}

      <button className="btn-recommend" onClick={handleSubmit} disabled={loading}>
        {loading ? 'Loading…' : '🎬 Get Recommendations'}
      </button>
    </div>
  )
}
