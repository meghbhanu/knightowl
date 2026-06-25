import { useState } from 'react'
import { Chessboard } from 'react-chessboard'
import { Chess } from 'chess.js'

export default function BoardPanel({ onMove }) {
  const [game, setGame] = useState(new Chess())
  const [moveHistory, setMoveHistory] = useState([])
  const [status, setStatus] = useState('White to move')
  const [fenBeforeMove, setFenBeforeMove] = useState(new Chess().fen())
  const [moveCount, setMoveCount] = useState(0)

  function getStatus(chess) {
    if (chess.isCheckmate()) return `Checkmate! ${chess.turn() === 'w' ? 'Black' : 'White'} wins`
    if (chess.isDraw()) return 'Draw'
    if (chess.isCheck()) return `${chess.turn() === 'w' ? 'White' : 'Black'} is in check`
    return `${chess.turn() === 'w' ? 'White' : 'Black'} to move`
  }

  function onPieceDrop({ sourceSquare, targetSquare, piece }) {
    try {
      const fenBefore = game.fen()
      const gameCopy = new Chess(fenBefore)
      const move = gameCopy.move({
        from: sourceSquare,
        to: targetSquare,
        promotion: 'q'
      })

      if (!move) {
        return false
      }

      const newMoveCount = moveCount + 1
      const fenAfter = gameCopy.fen()
      setGame(gameCopy)
      setStatus(getStatus(gameCopy))
      setMoveHistory(prev => [...prev, move.san])
      setMoveCount(newMoveCount)
      setFenBeforeMove(fenBefore)

      onMove({
        san: move.san,
        from: move.from,
        to: move.to,
        fen_before: fenBefore,
        fen_after: fenAfter,
        move_number: newMoveCount
      })

      return true
    } catch (error) {
      return false
    }
  }

  function resetGame() {
    const freshGame = new Chess()
    setGame(freshGame)
    setMoveHistory([])
    setStatus('White to move')
    setMoveCount(0)
    setFenBeforeMove(freshGame.fen())
  }

  return (
    <div style={styles.panel}>
      <div style={styles.header}>
        <span style={styles.title}>♟ Board</span>
        <span style={styles.status}>{status}</span>
        <button style={styles.resetBtn} onClick={resetGame}>New game</button>
      </div>

      <div style={styles.boardWrap}>
        <Chessboard
            options={{
            id: 'KnightOwlBoard',
            position: game.fen(),
            onPieceDrop,
            boardWidth: 440,
            allowDragging: true,
            allowDragOffBoard: false,
            showAnimations: true,
            isDraggablePiece: ({ piece }) => !!piece,
            customBoardStyle: {
              borderRadius: '8px',
              boxShadow: '0 2px 12px rgba(0,0,0,0.12)'
            },
            customDarkSquareStyle: { backgroundColor: '#b58863' },
            customLightSquareStyle: { backgroundColor: '#f0d9b5' },
          }}
        />
      </div>

      <div style={styles.moveList}>
        {moveHistory.length === 0 && (
          <p style={{ fontSize: '13px', color: 'var(--text-muted)' }}>No moves yet</p>
        )}
        {moveHistory.reduce((pairs, san, i) => {
          if (i % 2 === 0) pairs.push([san])
          else pairs[pairs.length - 1].push(san)
          return pairs
        }, []).map((pair, i) => (
          <div key={i} style={styles.movePair}>
            <span style={styles.moveNum}>{i + 1}.</span>
            <span style={styles.moveText}>{pair[0]}</span>
            <span style={styles.moveText}>{pair[1] || ''}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

const styles = {
  panel: { display: 'flex', flexDirection: 'column', height: '100%', background: 'var(--bg-panel)' },
  header: { padding: '14px 16px', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', gap: '12px' },
  title: { fontWeight: 500, fontSize: '15px' },
  status: { flex: 1, fontSize: '13px', color: 'var(--text-secondary)' },
  resetBtn: { fontSize: '12px', padding: '5px 12px', borderRadius: '6px', border: '1px solid var(--border)', background: 'var(--bg-secondary)', cursor: 'pointer' },
  boardWrap: { padding: '24px', display: 'flex', justifyContent: 'center', alignItems: 'center' },
  moveList: { flex: 1, overflowY: 'auto', padding: '12px 16px', display: 'flex', flexDirection: 'column', gap: '2px' },
  movePair: { display: 'grid', gridTemplateColumns: '28px 1fr 1fr', gap: '4px', fontSize: '13px', padding: '2px 0' },
  moveNum: { color: 'var(--text-muted)', fontVariantNumeric: 'tabular-nums' },
  moveText: { color: 'var(--text-primary)', fontFamily: 'monospace' },
}