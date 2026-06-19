import { useState, useRef, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import { sendChatMessage, analyseMoveRequest } from '../services/api'

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

export default function ChatPanel({ currentFen, lastMove }) {
    const [messages, setMessages] = useState([])  // { role, content }
    const [displayMessages, setDisplayMessages] = useState([  //what renders
       { role: 'assistant', label: 'TIP', content: "Hello! I'm KnightOwl, your chess coach. Make a move on the board, describe your position, or ask me anything about chess." }
    ])
    const [input, setInput] = useState('')
    const [loading, setLoading] = useState(false)
    const [analysing, setAnalysing] = useState(false)
    const [moveList, setMoveList] = useState([])
    const [tokenCount, setTokenCount] = useState(0)
    const bottomRef = useRef(null)

    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
    }, [displayMessages, loading, analysing])

     useEffect(() => {
    if (!lastMove) return
    setMoveList(prev => [...prev, lastMove.san])
    analyseMove(lastMove)
  }, [lastMove])

  async function analyseMove(move) {
    setAnalysing(true)
    try {
      const data = await analyseMoveRequest(move.san, move.from, move.to, move.fen)
      setDisplayMessages(prev => [...prev, {
        role: 'assistant',
        label: null,
        isCommentary: true,
        content: data.commentary
      }])
      setTokenCount(prev => prev + data.tokens_used)
    } catch (err) {
      console.error('Move analysis failed:', err)
    } finally {
      setAnalysing(false)
    }
  }

    async function handleSend(text) {
        const userText = text || input.trim()
        if (!userText || loading) return

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
          const assistantMsg = { role: 'assistant', content: data.reply }

          setMessages(prev => [...prev, assistantMsg].slice(-MAX_HISTORY))
          setDisplayMessages(prev => [...prev, { role: 'assistant', label: data.label, isCommentary: false, content: data.reply }])
          setTokenCount(prev => prev + data.tokens_used)
        } catch (err) {
          setDisplayMessages(prev => [...prev, {
              role: 'assistant',
              label: 'TIP',
              isCommentary: false,
              content: `Sorry, I had trouble responding: ${err.message}`
          }])
        } finally {
            setLoading(false)
        }
    }

  return (
    <div style={styles.panel}>
      <div style={styles.header}>
        <span style={styles.headerTitle}>♞ KnightOwl</span>
        <span style={styles.tokenBadge}>{tokenCount} tokens used</span>
      </div>

      <div style={styles.messages}>
        {displayMessages.map((msg, i) => (
          <div key={i} style={msg.role === 'user' ? styles.userBubbleWrap : styles.botBubbleWrap}>
            {msg.role === 'assistant' && (
              <div style={msg.isCommentary ? styles.commentaryBubble : styles.botBubble}>
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
          <button key={chip.label} style={styles.chip}
            onClick={() => handleSend(chip.text)}
            disabled={loading || analysing}>
            {chip.label}
          </button>
        ))}
      </div>

      <div style={styles.inputRow}>
        <textarea
          style={styles.textarea}
          placeholder="Ask the coach a question..."
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
          disabled={loading || !input.trim()}>
          ↑
        </button>
      </div>
    </div>
  )
}

const styles = {
  panel: { display: 'flex', flexDirection: 'column', height: '100%', background: 'var(--bg-primary)', borderLeft: '1px solid var(--border)' },
  header: { padding: '14px 16px', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'var(--accent)', color: '#fff' },
  headerTitle: { fontWeight: 500, fontSize: '15px' },
  tokenBadge: { fontSize: '11px', opacity: 0.7 },
  messages: { flex: 1, overflowY: 'auto', padding: '16px', display: 'flex', flexDirection: 'column', gap: '10px' },
  botBubbleWrap: { alignSelf: 'flex-start', maxWidth: '90%' },
  userBubbleWrap: { alignSelf: 'flex-end', maxWidth: '85%' },
  botBubble: { background: 'var(--bg-panel)', border: '1px solid var(--border)', borderRadius: '12px', padding: '10px 14px' },
  commentaryBubble: { background: 'var(--bg-secondary)', borderRadius: '8px', padding: '6px 12px', borderLeft: '3px solid var(--border)' },
  commentaryText: { fontSize: '13px', color: 'var(--text-secondary)', lineHeight: 1.5, fontStyle: 'italic' },
  botText: { fontSize: '14px', lineHeight: 1.6, color: 'var(--text-primary)' },
  userText: { background: 'var(--accent)', color: '#fff', padding: '10px 14px', borderRadius: '12px', fontSize: '14px', lineHeight: 1.5 },
  label: { display: 'inline-block', fontSize: '11px', fontWeight: 500, padding: '2px 8px', borderRadius: '10px', marginBottom: '6px' },
  thinking: { display: 'flex', gap: '5px', padding: '4px 0' },
  dot: { width: '7px', height: '7px', background: 'var(--text-muted)', borderRadius: '50%', animation: 'bounce 1.2s infinite' },
  chips: { padding: '8px 12px', display: 'flex', flexWrap: 'wrap', gap: '6px', borderTop: '1px solid var(--border)' },
  chip: { fontSize: '12px', padding: '5px 10px', borderRadius: '16px', border: '1px solid var(--border)', background: 'var(--bg-secondary)', cursor: 'pointer', color: 'var(--text-secondary)' },
  inputRow: { display: 'flex', gap: '8px', padding: '12px', borderTop: '1px solid var(--border)', alignItems: 'flex-end' },
  textarea: { flex: 1, resize: 'none', padding: '8px 12px', borderRadius: '8px', border: '1px solid var(--border)', fontSize: '14px', fontFamily: 'var(--font)', outline: 'none' },
  sendBtn: { width: '38px', height: '38px', borderRadius: '8px', background: 'var(--accent)', color: '#fff', border: 'none', cursor: 'pointer', fontSize: '18px' },
}