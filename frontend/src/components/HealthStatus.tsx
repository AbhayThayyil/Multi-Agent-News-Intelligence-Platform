import { useEffect, useState } from 'react'
import { fetchHealth, type HealthResponse } from '../api/health'

export function HealthStatus() {
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchHealth()
      .then(setHealth)
      .catch((err: Error) => setError(err.message))
  }, [])

  if (error) {
    return <p>Backend unreachable: {error}</p>
  }

  if (!health) {
    return <p>Checking backend health...</p>
  }

  return (
    <p>
      Backend status: {health.status} ({health.environment})
    </p>
  )
}
