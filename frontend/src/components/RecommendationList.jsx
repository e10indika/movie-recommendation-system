import React from 'react'
import MovieCard from './MovieCard'

const STRATEGY_LABELS = {
  popularity:      '🔥 Popular',
  content_based:   '🎭 Genre Filter',
  item_similarity: '🎬 Item Similarity',
  onboarding:      '⭐ Personalised',
}

export default function RecommendationList({
  recommendations, userId, loading, error, coldStart, coldStartStrategy,
}) {
  if (loading) return null

  if (error) {
    return (
      <div className="rec-container">
        <div className="error-box">⚠️ {error}</div>
      </div>
    )
  }

  if (!recommendations) return null

  if (recommendations.length === 0) {
    return (
      <div className="rec-container">
        <p className="empty-state">No recommendations found.</p>
      </div>
    )
  }

  const label = STRATEGY_LABELS[coldStartStrategy] || coldStartStrategy

  return (
    <div className="rec-container">
      <h2 className="rec-header">
        Showing top <span className="accent">{recommendations.length}</span> recommendations
        {userId != null && <> for <span className="accent">User #{userId}</span></>}
        {coldStart && label && (
          <span className="cold-start-strategy-tag"> · {label}</span>
        )}
      </h2>
      <div className="movie-grid">
        {recommendations.map((movie) => (
          <MovieCard key={movie.movie_id} movie={movie} />
        ))}
      </div>
    </div>
  )
}
