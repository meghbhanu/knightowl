import { useState, useRef, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import { sendChatMessage, analyseMoveRequest, getSessionBudget } from '../services/api'

const LABEL_STYLES = {
  CRITIQUE: { bg: 'var(--critique)', color: 'var(--critique-text)', text: 'critique' },
  PLAN:     { bg: 'var(--plan)',     color: 'var(--plan-text)',     text: 'plan' },
  OPENING:  { bg: 'var(--opening)', color: 'var(--opening-text)', text: 'opening' },
  TIP:      { bg: 'var(--tip)',      color: 'var(--tip-text)',      text: 'tip' },
}

const QUICK_CHIPS = [
  { label: '♟ Queen out early?', text: 'I moved my queen out early. Was that a mistake?' },
  { label: '⚔️ Kingside attack', text: 'I want to attack the kingside. Where do I start?' },
  { label: '📖 Opening principles', text: 'What are the key opening principles I should follow?' },
  { label: '♙ Passed pawn', text: 'I have a passed pawn. How do I convert it?' },
  { label: '🤔 Opponent castled', text: 'My opponent just castled. What should I think about now?' },
]

const MAX_HISTORY = 10  // frontend cap before sending to backend
const SESSION_KEY = 'knightowl_session_id'

function getQualityStyle(quality) {
  const styles = {
    brilliant: { background: '#dbeafe', color: '#1e40af' },
    good:      { background: '#dcfce7', color: '#166534' },
    inaccuracy:{ background: '#fef9c3', color: '#854d0e' },
    mistake:   { background: '#ffedd5', color: '#9a3412' },
    blunder:   { background: '#fee2e2', color: '#991b1b' },
    played:    { background: '#f3f4f6', color: '#374151' },
  }
  return styles[quality] || styles.played
}

export default function ChatPanel({ currentFen, lastMove }) {
  const [messages, setMessages] = useState([])  // { role, content }
  const [displayMessages, setDisplayMessages] = useState([  //what renders
       { role: 'assistant', label: null, isCommentary: false, content: "Hello! I'm KnightOwl, your chess coach. Make a move on the board, describe your position, or ask me anything about chess." }
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [analysing, setAnalysing] = useState(false)
  const [moveList, setMoveList] = useState([])
  const [tokenCount, setTokenCount] = useState(0)
  const [callsRemaining, setCallsRemaining] = useState(50)
  const [sessionExhausted, setSessionExhausted] = useState(false)
  const [sessionId, setSessionId] = useState(() => {
    return localStorage.getItem(SESSION_KEY) || null
  })
  const bottomRef = useRef(null)

  useEffect(() => {
    const storedId = localStorage.getItem(SESSION_KEY)
    if (storedId) {
      getSessionBudget(storedId).then(data => {
        setCallsRemaining(data.calls_remaining)
        setSessionExhausted(!data.has_budget)
      }).catch(() => {})
    }
  }, [])

  useEffect(() => {
      bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [displayMessages, loading, analysing])

  useEffect(() => {
    if (!lastMove) return
    setMoveList(prev => [...prev, lastMove.san])
    analyseMove(lastMove)
  }, [lastMove])

  function persistSession(id) {
    setSessionId(id)
    localStorage.setItem(SESSION_KEY, id)
  }

  function handleNewGame() {
    localStorage.removeItem(SESSION_KEY)
    setSessionId(null)
    setSessionExhausted(false)
    setCallsRemaining(50)
    setMessages([])
    setMoveList([])
    setTokenCount(0)
    setDisplayMessages([{
      role: 'assistant',
      label: null,
      isCommentary: false,
      content: "New game started! Make your first move and I'll analyse it."
    }])
    onNewGame()
  }

  async function analyseMove(move) {
    if (sessionExhausted) return
    setAnalysing(true)
    try {
      const data = await analyseMoveRequest(
        move.san,
        move.from,
        move.to,
        move.fen_before,
        move.fen_after,
        move.move_number,
        sessionId
      )

      if (data.session_id && !sessionId) persistSession(data.session_id)
      if (data.calls_remaining !== undefined) {
        setCallsRemaining(data.calls_remaining)
        if (data.calls_remaining <= 0) setSessionExhausted(true)
      }

      setDisplayMessages(prev => [...prev, {
        role: 'assistant',
        label: null,
        isCommentary: true,
        content: data.commentary,
        move_quality: data.move_quality,
        score_display: data.score_display
      }])
      setTokenCount(prev => prev + data.tokens_used)
    } catch (err) {
      if (err.message.includes('429') || err.message.includes('Session limit')) {
        setSessionExhausted(true)
        setCallsRemaining(0)
      }
      console.error('Move analysis failed:', err)
    } finally {
      setAnalysing(false)
    }
  }

    async function handleSend(text) {
        const userText = text || input.trim()
        if (!userText || loading || sessionExhausted) return
        
        const context = moveList.length > 0
          ? `\n\n[Moves played so far: ${moveList.join(', ')}]\n[Current board FEN: ${currentFen}]`
          : `\n\n[Current board FEN: ${currentFen}]`

        setInput('')

        const userMsg = {
            role: 'user',
            content: `${userText}${context}`
        }

        const displayMsg = { role: 'user', content: userText }  // clean version for UI
        const newMessages = [...messages, userMsg].slice(-MAX_HISTORY)
        setMessages(newMessages)
        setDisplayMessages(prev => [...prev, displayMsg])
        setLoading(true)

        try {
          const data = await sendChatMessage(newMessages)

          if (data.session_id && !sessionId) persistSession(data.session_id)
          if (data.calls_remaining !== undefined) {
            setCallsRemaining(data.calls_remaining)
            if (data.calls_remaining <= 0) setSessionExhausted(true)
          }

          const assistantMsg = { role: 'assistant', content: data.reply }

          setMessages(prev => [...prev, assistantMsg].slice(-MAX_HISTORY))
          setDisplayMessages(prev => [...prev, { role: 'assistant', label: data.label, isCommentary: false, content: data.reply }])
          setTokenCount(prev => prev + data.tokens_used)
        } catch (err) {
          if (err.message.includes('429') || err.message.includes('Session limit')) {
            setSessionExhausted(true)
            setCallsRemaining(0)
            setDisplayMessages(prev => [...prev, {
              role: 'assistant',
              label: 'TIP',
              isCommentary: false,
              content: "You've used all your coaching interactions for this session. Click 'New game' to start fresh."
            }])
          }else {
            setDisplayMessages(prev => [...prev, {
              role: 'assistant',
              label: 'TIP',
              isCommentary: false,
              content: `Sorry, I had trouble responding. Please try again.`
            }])
          }  
        } finally {
            setLoading(false)
        }
    }

  const budgetPct = (callsRemaining / 50) * 100
  const budgetColor = budgetPct > 50
    ? '#22c55e'
    : budgetPct > 20
    ? '#f59e0b'
    : '#ef4444'

  return (
    <div style={styles.panel}>
      <div style={styles.header}>
        <div>
          <span style={styles.headerTitle}>♞ KnightOwl</span>
          <div style={styles.budgetRow}>
            <div style={styles.budgetTrack}>
              <div style={{
                ...styles.budgetFill,
                width: `${budgetPct}%`,
                background: budgetColor
              }} />
            </div>
            <span style={styles.budgetLabel}>
              {sessionExhausted ? 'Session complete' : `${callsRemaining} interactions left`}
            </span>
          </div>
        </div>
          <button style={styles.newGameBtn} onClick={handleNewGame}>
          New game
        </button>
      </div>

      {/* Session exhausted banner */}
      {sessionExhausted && (
        <div style={styles.exhaustedBanner}>
          Session limit reached. Click <strong>New game</strong> to continue coaching.
        </div>
      )}        

      <div style={styles.messages}>
        {displayMessages.map((msg, i) => (
          <div key={i} style={msg.role === 'user' ? styles.userBubbleWrap : styles.botBubbleWrap}>
            {msg.role === 'assistant' && (
              <div style={msg.isCommentary ? styles.commentaryBubble : styles.botBubble}>
                {msg.move_quality && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                    <span style={{
                      ...styles.qualityBadge,
                      ...getQualityStyle(msg.move_quality)
                    }}>
                      {msg.move_quality}
                    </span>
                    {msg.score_display && (
                      <span style={styles.scoreDisplay}>{msg.score_display}</span>
                    )}
                  </div>
                )}
                {msg.label && (
                  <span style={{
                    ...styles.label,
                    background: LABEL_STYLES[msg.label]?.bg,
                    color: LABEL_STYLES[msg.label]?.color
                  }}>
                    {LABEL_STYLES[msg.label]?.text}
                  </span>
                )}
                {msg.isCommentary
                  ? <p style={styles.commentaryText}>{msg.content}</p>
                  : <div style={styles.botText}><ReactMarkdown>{msg.content}</ReactMarkdown></div>
                }
              </div>
            )}
            {msg.role === 'user' && (
              <div style={styles.userText}>{msg.content}</div>
            )}
          </div>
        ))}

        {analysing && (
          <div style={styles.botBubbleWrap}>
            <div style={styles.commentaryBubble}>
              <p style={styles.commentaryText}>analysing move...</p>
            </div>
          </div>
        )}

        {loading && (
          <div style={styles.botBubbleWrap}>
            <div style={styles.botBubble}>
              <div style={styles.thinking}>
                <span style={{...styles.dot, animationDelay: '0s'}} />
                <span style={{...styles.dot, animationDelay: '0.2s'}} />
                <span style={{...styles.dot, animationDelay: '0.4s'}} />
              </div>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div style={styles.chips}>
        {QUICK_CHIPS.map(chip => (
          <button key={chip.label} style={{
            ...styles.chip,
            opacity: sessionExhausted ? 0.4 : 1,
            cursor: sessionExhausted ? 'not-allowed' : 'pointer'
          }}
            onClick={() => handleSend(chip.text)}
            disabled={loading || analysing || sessionExhausted}>
            {chip.label}
          </button>
        ))}
      </div>

      <div style={styles.inputRow}>
        <textarea
          style={{
            ...styles.textarea,
            opacity: sessionExhausted ? 0.5 : 1
          }}
          placeholder={sessionExhausted
            ? "Session complete — click New game to continue"
            : "Ask the coach a question..."
          }
          value={input}
          maxLength={400}
          rows={2}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => {
            if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend() }
          }}
        />
        <button style={styles.sendBtn}
          onClick={() => handleSend()}
          disabled={loading || !input.trim() || sessionExhausted}>
          ↑
        </button>
      </div>
    </div>
  )
}

const styles = {
  panel: { display: 'flex', flexDirection: 'column', height: '100%', background: 'var(--bg-primary)', borderLeft: '1px solid var(--border)' },
  header: { padding: '10px 16px', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'var(--accent)', color: '#fff' },
  headerTitle: { fontWeight: 500, fontSize: '15px', display: 'block' },
  budgetRow: { display: 'flex', alignItems: 'center', gap: '8px', marginTop: '4px' },
  budgetTrack: { width: '80px', height: '4px', background: 'rgba(255,255,255,0.3)', borderRadius: '2px' },
  budgetFill: { height: '100%', borderRadius: '2px', transition: 'width 0.4s, background 0.4s' },
  budgetLabel: { fontSize: '11px', opacity: 0.85 },
  newGameBtn: { fontSize: '12px', padding: '6px 12px', borderRadius: '6px', border: '1px solid rgba(255,255,255,0.4)', background: 'transparent', color: '#fff', cursor: 'pointer' },
  exhaustedBanner: { padding: '10px 16px', background: '#fef2f2', borderBottom: '1px solid #fecaca', fontSize: '13px', color: '#991b1b', textAlign: 'center' },
  messages: { flex: 1, overflowY: 'auto', padding: '16px', display: 'flex', flexDirection: 'column', gap: '10px' },
  botBubbleWrap: { alignSelf: 'flex-start', maxWidth: '90%' },
  userBubbleWrap: { alignSelf: 'flex-end', maxWidth: '85%' },
  botBubble: { background: 'var(--bg-panel)', border: '1px solid var(--border)', borderRadius: '12px', padding: '10px 14px' },
  commentaryBubble: { background: 'var(--bg-secondary)', borderRadius: '8px', padding: '6px 12px', borderLeft: '3px solid var(--border)' },
  commentaryText: { fontSize: '13px', color: 'var(--text-secondary)', lineHeight: 1.5, fontStyle: 'italic' },
  botText: { fontSize: '14px', lineHeight: 1.6, color: 'var(--text-primary)' },
  userText: { background: 'var(--accent)', color: '#fff', padding: '10px 14px', borderRadius: '12px', fontSize: '14px', lineHeight: 1.5 },
  label: { display: 'inline-block', fontSize: '11px', fontWeight: 500, padding: '2px 8px', borderRadius: '10px', marginBottom: '6px' },
  qualityRow: { display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' },
  qualityBadge: { fontSize: '11px', fontWeight: 500, padding: '2px 8px', borderRadius: '10px', textTransform: 'capitalize' },
  scoreDisplay: { fontSize: '12px', fontFamily: 'monospace', color: 'var(--text-secondary)' },
  thinking: { display: 'flex', gap: '5px', padding: '4px 0' },
  dot: { width: '7px', height: '7px', background: 'var(--text-muted)', borderRadius: '50%', animation: 'bounce 1.2s infinite' },
  chips: { padding: '8px 12px', display: 'flex', flexWrap: 'wrap', gap: '6px', borderTop: '1px solid var(--border)' },
  chip: { fontSize: '12px', padding: '5px 10px', borderRadius: '16px', border: '1px solid var(--border)', background: 'var(--bg-secondary)', color: 'var(--text-secondary)' },
  inputRow: { display: 'flex', gap: '8px', padding: '12px', borderTop: '1px solid var(--border)', alignItems: 'flex-end' },
  textarea: { flex: 1, resize: 'none', padding: '8px 12px', borderRadius: '8px', border: '1px solid var(--border)', fontSize: '14px', fontFamily: 'var(--font)', outline: 'none' },
  sendBtn: { width: '38px', height: '38px', borderRadius: '8px', background: 'var(--accent)', color: '#fff', border: 'none', cursor: 'pointer', fontSize: '18px' },
}