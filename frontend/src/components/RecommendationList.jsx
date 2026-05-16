import React from 'react'
import MovieCard from './MovieCard'

export default function RecommendationList({ recommendations, userId, loading, error }) {
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
        <p className="empty-state">No recommendations found for User #{userId}.</p>
      </div>
    )
  }

  return (
    <div className="rec-container">
      <h2 className="rec-header">
        Showing top <span className="accent">{recommendations.length}</span> recommendations for{' '}
        <span className="accent">User #{userId}</span>
      </h2>
      <div className="movie-grid">
        {recommendations.map((movie) => (
          <MovieCard key={movie.movie_id} movie={movie} />
        ))}
      </div>
    </div>
  )
}
