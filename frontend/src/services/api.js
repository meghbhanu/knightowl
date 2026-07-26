const API_BASE = import.meta.env.VITE_API_URL || '/api/v1'

export async function sendChatMessage(messages, sessionId = null) {
  const response = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ messages, session_id: sessionId })
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({}))
    throw new Error(error.detail || `API error ${response.status}`)
  }

  return response.json()  // { reply, label, tokens_used, session_id }
}

export async function analyseMoveRequest(san, from_sq, to_sq, fen_before, fen_after, move_number, sessionId = null) {
  const response = await fetch(`${API_BASE}/analyse`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ san, from_sq, to_sq, fen_before, fen_after, move_number, session_id: sessionId })
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({}))
    throw new Error(error.detail || `API error ${response.status}`)
  }

  return response.json()  // { commentary, tokens_used }
}

export async function getSessionBudget(sessionId) {
  const response = await fetch(`${API_BASE}/session/${sessionId}/budget`)
  if (!response.ok) throw new Error('Could not fetch session budget')
  return response.json()
}