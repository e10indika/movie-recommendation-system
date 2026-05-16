import React, { useState } from 'react'

export default function UserSelector({
  users,
  selectedUser,
  onSelectUser,
  onGetRecommendations,
  loading,
}) {
  const [manualId, setManualId] = useState('')
  const [useManual, setUseManual] = useState(false)

  function handleSubmit(e) {
    e.preventDefault()
    const id = useManual ? parseInt(manualId, 10) : selectedUser
    if (!id || isNaN(id)) return
    onGetRecommendations(id)
  }

  return (
    <div className="user-selector">
      <h2>Select a User</h2>
      <p className="user-count">
        {users.length > 0 ? `${users.length} users available` : 'Loading users…'}
      </p>

      <form onSubmit={handleSubmit} className="selector-form">
        <div className="input-toggle">
          <button
            type="button"
            className={`toggle-btn ${!useManual ? 'active' : ''}`}
            onClick={() => setUseManual(false)}
          >
            Dropdown
          </button>
          <button
            type="button"
            className={`toggle-btn ${useManual ? 'active' : ''}`}
            onClick={() => setUseManual(true)}
          >
            Manual Entry
          </button>
        </div>

        {useManual ? (
          <input
            type="number"
            className="user-input"
            placeholder="Enter User ID (e.g. 42)"
            value={manualId}
            onChange={(e) => setManualId(e.target.value)}
            min="1"
          />
        ) : (
          <select
            className="user-select"
            value={selectedUser || ''}
            onChange={(e) => onSelectUser(Number(e.target.value))}
          >
            <option value="" disabled>
              — Choose a user ID —
            </option>
            {users.map((uid) => (
              <option key={uid} value={uid}>
                User #{uid}
              </option>
            ))}
          </select>
        )}

        <button
          type="submit"
          className="btn-recommend"
          disabled={loading || (!useManual && !selectedUser) || (useManual && !manualId)}
        >
          {loading ? 'Loading…' : '🎬 Get Recommendations'}
        </button>
      </form>
    </div>
  )
}
