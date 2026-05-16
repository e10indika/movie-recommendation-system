import axios from 'axios'

const api = axios.create({
  baseURL: 'http://localhost:8003/api/v1',
  timeout: 30000,
})

export const getHealth  = ()           => api.get('/health')
export const getUsers   = ()           => api.get('/users')
export const getMovies  = ()           => api.get('/movies')
export const getRecommendations = (userId, n = 10, strategy = 'popularity') =>
  api.get(`/recommend/${userId}`, { params: { n, strategy } })

// Cold-start explicit endpoints
export const getPopular   = (n = 10)                     => api.get('/cold-start/popular', { params: { n } })
export const getByGenre   = (genres, n = 10)             => api.get('/cold-start/by-genre', { params: { genres, n } })
export const getSimilarTo = (movieId, n = 10)            => api.get(`/cold-start/similar-to/${movieId}`, { params: { n } })
export const getOnboarding = (seedRatings, n = 10)       =>
  api.post('/cold-start/onboarding', { n, seed_ratings: seedRatings })

export default api
