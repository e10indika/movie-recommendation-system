import React from 'react'

export default function LoadingSpinner({ message = 'Loading…' }) {
  return (
    <div className="spinner-container">
      <div className="spinner" />
      <p className="spinner-message">{message}</p>
    </div>
  )
}
