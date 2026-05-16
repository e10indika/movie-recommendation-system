import React, { useEffect, useState } from 'react'
import { getRecommendations, getUsers } from './services/api'
import LoadingSpinner from './components/LoadingSpinner'
import RecommendationList from './components/RecommendationList'
import UserSelector from './components/UserSelector'
import './App.css'

export default function App() {
  const [users, setUsers]               = useState([])
  const [selectedUser, setSelectedUser] = useState(null)
  const [recommendations, setRecommendations] = useState(null)
  const [loading, setLoading]           = useState(false)
  const [error, setError]               = useState(null)
  const [recUserId, setRecUserId]       = useState(null)

  useEffect(() => {
    getUsers()
      .then((res) => setUsers(res.data.users || []))
      .catch(() => setUsers([]))
  }, [])

  async function handleGetRecommendations(userId) {
    setLoading(true)
    setError(null)
    setRecommendations(null)
    setRecUserId(userId)
    try {
      const res = await getRecommendations(userId, 10)
      setRecommendations(res.data.recommendations || [])
    } catch (err) {
      const detail = err.response?.data?.detail
      setError(
        err.response?.status === 503
          ? '🔧 Model not trained yet. Run train_and_save.py first.'
          : err.response?.status === 404
          ? `User #${userId} not found in training data.`
          : detail || 'Unable to reach the recommendation server.',
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>🎬 Movie Recommendation System</h1>
        <p className="subtitle">Powered by Apache Spark MLlib ALS Collaborative Filtering</p>
      </header>

      <main className="app-main">
        <UserSelector
          users={users}
          selectedUser={selectedUser}
          onSelectUser={setSelectedUser}
          onGetRecommendations={handleGetRecommendations}
          loading={loading}
        />

        {loading && <LoadingSpinner message="Generating recommendations with Spark ALS…" />}

        <RecommendationList
          recommendations={recommendations}
          userId={recUserId}
          loading={loading}
          error={error}
        />
      </main>

      <footer className="app-footer">
        <p>
          Built with{' '}
          <strong>PySpark MLlib</strong> · <strong>FastAPI</strong> · <strong>React</strong> ·{' '}
          <strong>Vite</strong>
        </p>
      </footer>
    </div>
  )
}
