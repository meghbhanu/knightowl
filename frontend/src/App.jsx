import { useState } from 'react'
import BoardPanel from './components/BoardPanel'
import ChatPanel from './components/ChatPanel'

export default function App() {
  const [lastMove, setLastMove] = useState(null)
  const [currentFen, setCurrentFen] = useState(
    'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'
  )

  function handleMove(move) {
    setLastMove(move)
    setCurrentFen(move.fen)
  }

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '500px 1fr', height: '100vh' }}>
      <div style={{ height: '100vh', borderRight: '1px solid #e5e4e0' }}>
        <BoardPanel onMove={handleMove} />
      </div>
      <div style={{ height: '100vh' }}>
        <ChatPanel currentFen={currentFen} lastMove={lastMove} />
      </div>
    </div>
  )
}