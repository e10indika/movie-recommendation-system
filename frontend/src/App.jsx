import React, { useEffect, useState } from 'react'
import { getRecommendations, getUsers } from './services/api'
import ColdStartPanel from './components/ColdStartPanel'
import LoadingSpinner from './components/LoadingSpinner'
import RecommendationList from './components/RecommendationList'
import UserSelector from './components/UserSelector'
import './App.css'

export default function App() {
  const [users, setUsers]               = useState([])
  const [selectedUser, setSelectedUser] = useState(null)
  const [recData, setRecData]           = useState(null)   // full response object
  const [loading, setLoading]           = useState(false)
  const [error, setError]               = useState(null)
  const [pendingUserId, setPendingUserId] = useState(null) // user that triggered cold-start

  useEffect(() => {
    getUsers()
      .then((res) => setUsers(res.data.users || []))
      .catch(() => setUsers([]))
  }, [])

  async function handleGetRecommendations(userId) {
    setLoading(true)
    setError(null)
    setRecData(null)
    setPendingUserId(null)
    try {
      const res = await getRecommendations(userId, 10)
      const data = res.data
      if (data.cold_start) {
        // ALS had no data — show the cold-start panel instead of empty results
        setPendingUserId(userId)
      } else {
        setRecData(data)
      }
    } catch (err) {
      setError(
        err.response?.status === 503
          ? '🔧 Model not trained yet. Run: bash run.sh train'
          : err.response?.data?.detail || 'Unable to reach the recommendation server.',
      )
    } finally {
      setLoading(false)
    }
  }

  // Called when ColdStartPanel successfully fetches results
  function handleColdStartResult(data) {
    setPendingUserId(null)
    setRecData(data)
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

        {/* Cold-start panel — shown when user is new */}
        {!loading && pendingUserId && (
          <ColdStartPanel
            userId={pendingUserId}
            onResult={handleColdStartResult}
          />
        )}

        {/* Normal results (ALS or cold-start strategy) */}
        {!loading && !pendingUserId && (
          <RecommendationList
            recommendations={recData?.recommendations ?? null}
            userId={recData?.user_id ?? null}
            coldStart={recData?.cold_start ?? false}
            coldStartStrategy={recData?.cold_start_strategy ?? null}
            loading={loading}
            error={error}
          />
        )}
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
