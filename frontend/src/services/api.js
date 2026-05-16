import axios from 'axios'

const api = axios.create({
  baseURL: 'http://localhost:8003/api/v1',
  timeout: 30000,
})

export const getHealth = () => api.get('/health')
export const getUsers = () => api.get('/users')
export const getMovies = () => api.get('/movies')
export const getRecommendations = (userId, n = 10) =>
  api.get(`/recommend/${userId}`, { params: { n } })

export default api
