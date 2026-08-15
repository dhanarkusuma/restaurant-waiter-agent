# Restaurant Waiter Agent

AI-powered restaurant waiter ordering system via Telegram with restaurant management dashboard.

## System Architecture

- **Backend**: FastAPI (Python >= 3.11), SQLAlchemy 2.0, PostgreSQL
- **AI Agent**: Google ADK (Agent Development Kit), Gemini models
- **Customer Channel**: Telegram Bot API
- **Management Dashboard**: React, Tailwind CSS
- **Persistence**: PostgreSQL (Single source of truth)

## Monorepo Layout

```text
restaurant-waiter-agent/
├── .agents/                    # Google Agents CLI workspace skills
├── .agents-cli-spec.md         # Agents CLI specification entry point
├── spec/
│   ├── requirements.md         # Product requirements
│   └── architecture.md         # Technical architecture
├── apps/
│   ├── backend/                # FastAPI application
│   │   ├── app/
│   │   │   ├── api/            # REST API endpoints & Webhooks
│   │   │   ├── auth/           # JWT authentication
│   │   │   ├── models/         # SQLAlchemy ORM models
│   │   │   ├── repositories/   # Data access layer
│   │   │   ├── schemas/        # Pydantic schemas
│   │   │   ├── services/       # Core business logic
│   │   │   └── main.py         # App entry point
│   │   └── tests/
│   └── dashboard/              # React + Tailwind admin dashboard
│       └── src/
├── agent/                      # Google ADK Agent
│   ├── agents/                 # Agent definitions
│   ├── prompts/                # Personas & instructions
│   ├── tools/                  # Explicit backend tools
│   └── tests/                  # Agent evals & unit tests
├── migrations/                 # Alembic database migrations
├── tests/                      # End-to-end & integration tests
├── docker-compose.yml          # PostgreSQL container
└── pyproject.toml              # Python dependencies & workspace config
```

## Getting Started

1. Copy `.env.example` to `.env` and configure your environment variables.
2. Start PostgreSQL: `docker compose up -d`
3. Install dependencies: `uv sync`
