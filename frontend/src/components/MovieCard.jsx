import React from 'react'

const GENRE_COLOURS = [
  '#e94560', '#0f3460', '#533483', '#05c46b',
  '#f8b739', '#1289a7', '#d63031', '#6c5ce7',
]

function genreColour(genre) {
  let hash = 0
  for (let i = 0; i < genre.length; i++) hash = genre.charCodeAt(i) + ((hash << 5) - hash)
  return GENRE_COLOURS[Math.abs(hash) % GENRE_COLOURS.length]
}

function StarRating({ rating }) {
  const display = Math.min(Math.max(rating, 0), 5)   // clamp to [0, 5] for display
  const full  = Math.floor(display)
  const half  = display - full >= 0.5
  const empty = 5 - full - (half ? 1 : 0)
  return (
    <span className="star-rating" title={`${rating.toFixed(2)} predicted`}>
      {'★'.repeat(full)}
      {half ? '½' : ''}
      {'☆'.repeat(empty)}
      <span className="rating-value"> {rating.toFixed(2)}</span>
    </span>
  )
}

export default function MovieCard({ movie }) {
  const genres = movie.genres
    ? movie.genres.split('|').filter(Boolean)
    : ['Unknown']

  return (
    <div className="movie-card">
      <h3 className="movie-title">{movie.title}</h3>
      <div className="genre-pills">
        {genres.map((g) => (
          <span
            key={g}
            className="genre-pill"
            style={{ backgroundColor: genreColour(g) }}
          >
            {g}
          </span>
        ))}
      </div>
      <div className="movie-rating">
        <StarRating rating={movie.predicted_rating} />
      </div>
    </div>
  )
}
