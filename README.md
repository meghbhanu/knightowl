# KnightOwl ♞

An AI-powered chess coaching application. Play on an interactive board and receive 
real-time move analysis powered by Stockfish engine evaluation fed into Claude AI — 
the same approach Chess.com uses for game review, delivered move by move as you play.

![KnightOwl Screenshot](docs/screenshot.png)

## Features

- **Real chessboard** — drag and drop pieces with full move validation via chess.js
- **Engine-grounded coaching** — Stockfish evaluates every move, Claude explains it in plain English
- **Move classification** — brilliant / good / inaccuracy / mistake / blunder with centipawn scores
- **AI chat coach** — ask questions about your position, opening, or plan
- **Session persistence** — every game and conversation stored in PostgreSQL
- **Redis caching** — identical positions served from cache, reducing API costs

## Architecture
┌─────────────────┐     ┌──────────────────────────────────────┐
│   React + Vite  │────▶│            FastAPI Backend           │
│  react-chessboard│     │                                      │
│    chess.js     │     │  ┌─────────────┐  ┌───────────────┐  │
└─────────────────┘     │  │  Stockfish  │  │ Anthropic API │  │
│  │  (engine)   │──▶  Claude AI   │  │
│  └─────────────┘  └───────────────┘  │
│         │                             │
│  ┌──────▼──────┐  ┌───────────────┐  │
│  │ PostgreSQL  │  │     Redis     │  │
│  │  Sessions  │  │    Cache      │  │
│  │   Moves    │  │ Rate Limiting │  │
│  │  Messages  │  └───────────────┘  │
│  └─────────────┘                     │
└──────────────────────────────────────┘

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, Vite, react-chessboard, chess.js |
| Backend | FastAPI, Python 3.11, Pydantic, SlowAPI |
| AI | Anthropic Claude API (claude-sonnet-4-6) |
| Chess Engine | Stockfish 16 |
| Database | PostgreSQL 15, SQLAlchemy, Alembic |
| Cache | Redis 7 |
| Container | Docker, Docker Compose |
| Orchestration | Kubernetes, Kustomize |
| CI/CD | GitHub Actions, ArgoCD |

## How the move analysis works

Every move triggers a two-step pipeline:

1. **Stockfish evaluates** the position before and after the move in centipawns, 
   always normalised to White's perspective. The delta is calculated from the moving 
   player's perspective and classified as brilliant/good/inaccuracy/mistake/blunder 
   with loosened thresholds in the opening (moves 1-20) where engine variance is higher.

2. **Claude receives the engine data** — score before, score after, classification, 
   and the engine's preferred move — and generates a 2-3 sentence coaching response 
   grounded in that data. The AI explains *why* the move was a mistake and what 
   concept was involved, not just that it was bad.

## Quick start

### Prerequisites
- Docker and Docker Compose
- Git LFS (for Stockfish binary)

```bash
git clone https://github.com/meghbhanu/knightowl
cd knightowl
git lfs pull
```

Create a `.env` file in the project root:
```env
ANTHROPIC_API_KEY=sk-ant-your-key-here
POSTGRES_USER=knightowl
POSTGRES_PASSWORD=your-password
POSTGRES_DB=knightowl
```

Run the full stack:
```bash
docker-compose up --build
```

Open `http://localhost` — the app is running.

### Local development (without Docker)

**Backend:**
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env       # fill in your values
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

**Services** (requires Docker):
```bash
docker-compose -f docker-compose.dev.yml up -d
```

### Kubernetes

```bash
# Start minikube
minikube start --driver=docker

# Create namespace and secrets
kubectl apply -f k8s/base/namespace.yaml
kubectl create secret generic knightowl-secrets \
  --namespace=knightowl \
  --from-literal=ANTHROPIC_API_KEY=your-key \
  --from-literal=POSTGRES_PASSWORD=your-password \
  --from-literal=POSTGRES_USER=knightowl \
  --from-literal=POSTGRES_DB=knightowl

# Deploy
kubectl apply -k k8s/overlays/dev

# Watch pods come up
kubectl get pods -n knightowl -w
```

## CI/CD

GitHub Actions runs on every push:
- **Backend CI** — pytest → Docker build → push to GHCR → update K8s manifest
- **Frontend CI** — Vite build → Docker build → push to GHCR → update K8s manifest

ArgoCD watches the Git repo and automatically syncs manifest changes to the cluster.
Rollback = `git revert` + push.

## Project structure
knightowl/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI app + CORS + rate limiting
│   │   ├── database.py             # SQLAlchemy engine + session
│   │   ├── redis_client.py         # Redis singleton
│   │   ├── routers/chat.py         # /chat and /analyse endpoints
│   │   ├── services/
│   │   │   ├── ai_service.py       # Anthropic proxy + history trimming
│   │   │   ├── stockfish_service.py # Engine evaluation + move classification
│   │   │   ├── session_service.py  # DB persistence helpers
│   │   │   ├── cache.py            # Redis get/set
│   │   │   └── prompt.py           # System prompt
│   │   ├── models/game.py          # SQLAlchemy models
│   │   └── schemas/chat.py         # Pydantic request/response schemas
│   ├── tests/
│   ├── alembic/                    # DB migrations
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx                 # Root layout + shared state
│   │   ├── components/
│   │   │   ├── BoardPanel.jsx      # Chessboard + move history
│   │   │   └── ChatPanel.jsx       # AI chat + move commentary
│   │   └── services/api.js         # Fetch wrapper for backend
│   ├── Dockerfile                  # Multi-stage Node build + Nginx
│   └── nginx.conf                  # Serve React + proxy /api/
├── k8s/
│   ├── base/                       # K8s manifests
│   └── overlays/dev|prod/          # Kustomize overlays
├── .github/workflows/              # GitHub Actions CI
├── docker-compose.yml              # Full stack local
└── docker-compose.dev.yml          # Dev services only