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
│   │   ├── scripts/            # Backend CLI & admin seeder scripts
│   │   └── tests/
│   └── dashboard/              # React + Tailwind admin dashboard
│       └── src/
├── agent/                      # Google ADK Agent
│   ├── agents/                 # Agent definitions
│   ├── prompts/                # Personas & instructions
│   ├── tools/                  # Explicit backend tools
│   └── tests/                  # Agent evals & unit tests
├── migrations/                 # Alembic database migrations
├── scripts/                    # Helper & seed runner scripts
├── tests/                      # End-to-end & integration tests
├── docker-compose.yml          # PostgreSQL container
└── pyproject.toml              # Python dependencies & workspace config
```

## Getting Started

### 1. Environment Configuration

Copy `.env.example` to `.env` and configure your environment variables:
```bash
cp .env.example .env
```

### 2. Start PostgreSQL Database

```bash
docker compose up -d
```

### 3. Install Dependencies

```bash
# Install backend dependencies
uv sync --extra dev

# Install dashboard dependencies
cd apps/dashboard && npm install && cd ../..
```

### 4. Run Database Migrations

```bash
uv run alembic upgrade head
```

### 5. Seed Initial Admin Account

Seed the initial administrator account idempotently using environment variables (never hardcoded in source code):

```bash
ADMIN_USERNAME=admin ADMIN_PASSWORD=your_secure_password ADMIN_FULL_NAME="Super Administrator" uv run python -m apps.backend.scripts.seed_admin
```

Atau menggunakan script runner:
```bash
ADMIN_USERNAME=admin ADMIN_PASSWORD=your_secure_password uv run python scripts/seed_admin.py
```

> [!NOTE]
> Perintah seeder bersifat **idempoten**. Jika user admin dengan username tersebut sudah terdaftar, seeder akan mendeteksinya dan tidak membuat duplikat.

### 6. Run Application

```bash
# Start FastAPI backend
uv run uvicorn apps.backend.app.main:app --reload --port 8000

# Start React Admin Dashboard (in another terminal)
cd apps/dashboard && npm run dev
```

### 7. Run Test Suite

```bash
uv run --extra dev pytest
```
