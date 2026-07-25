import { useState } from 'react'
import BoardPanel from './components/BoardPanel'
import ChatPanel from './components/ChatPanel'

export default function App() {
  const [lastMove, setLastMove] = useState(null)
  const [currentFen, setCurrentFen] = useState(
    'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'
  )
  const [boardKey, setBoardKey] = useState(0)

  function handleMove(move) {
    setLastMove(move)
    setCurrentFen(move.fen)
  }

  function handleNewGame() {
    setBoardKey(prev => prev + 1)   // remounts BoardPanel → resets chess.js state
    setLastMove(null)
    setCurrentFen('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1')
  }

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '500px 1fr', height: '100vh' }}>
      <div style={{ height: '100vh', borderRight: '1px solid #e5e4e0' }}>
        <BoardPanel key={boardKey} onMove={handleMove} />
      </div>
      <div style={{ height: '100vh' }}>
        <ChatPanel currentFen={currentFen} lastMove={lastMove} onNewGame={handleNewGame}/>
      </div>
    </div>
  )
}