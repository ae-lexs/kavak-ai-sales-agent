# Kavak AI Sales Agent

AI-powered sales agent built with FastAPI using Clean Architecture (Ports & Adapters pattern).

## Quickstart

Get the project running locally in under 2 minutes.

### Prerequisites

- Python 3.9+
- pip
- make (optional, but recommended)

### Setup

1. **Create a virtual environment:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements-dev.txt
   ```

3. **Run the server:**
   ```bash
   make dev
   # Or manually: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

   The API will be available at `http://localhost:8000`

4. **Run tests:**
   ```bash
   make test
   # Or manually: pytest -q
   ```

### Try It Out

**Health check:**
```bash
curl http://localhost:8000/health
```

**Chat endpoint:**
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test_session",
    "message": "Estoy buscando un auto familiar",
    "channel": "api"
  }'
```

**Run the demo script:**
```bash
chmod +x scripts/demo.sh
./scripts/demo.sh
```

The demo script simulates a full conversation flow in Spanish (RAG/FAQ → need → budget → options → financing → lead capture → handoff).

## Documentation

- [Agent Contract](docs/AGENT_CONTRACT.md) – defines the conversational contract, flow, and guarantees.
- [Demo Guide](docs/DEMO.md) – step-by-step 3-minute demo script (WhatsApp + backup).
- [Terraform Infrastructure](infra/terraform/README.md) – Reproducible AWS infrastructure defined with Terraform, including networking, compute, persistence, caching, and HTTPS setup.

## Features

- **Commercial Flow**: Guided conversation to understand customer needs, budget, preferences, and financing requirements
- **Car Catalog Search**: Search and recommend cars from CSV catalog based on customer criteria
- **Financing Calculator**: Calculate financing plans with multiple terms (36, 48, 60, 72 months)
- **FAQ RAG**: Answer frequently asked questions using Retrieval-Augmented Generation (RAG) from knowledge base
- **LLM-Powered Responses** (Optional): Natural language generation for FAQ responses using OpenAI, with deterministic fallback
- **Lead Capture**: Capture customer contact information (name, phone, preferred contact time) when they express purchase intent
- **WhatsApp Integration**: Webhook endpoint for Twilio/WhatsApp integration (`/channels/whatsapp/webhook`)
- **Idempotency Protection**: Redis-based idempotency for Twilio webhook to prevent duplicate replies on retries
- **State Caching**: Redis cache-aside pattern for conversation state to reduce database load
- **Spanish Language Support**: All user-facing messages are in Spanish
- **Clean Architecture**: Well-structured codebase following Ports & Adapters pattern

### Available Make Targets

- `make dev` - Run FastAPI development server with auto-reload
- `make test` - Run test suite with minimal output
- `make test_coverage` - Run tests with coverage report
- `make lint` - Check code formatting and linting (read-only)
- `make format_fix` - Automatically format code
- `make lint_fix` - Automatically fix linting issues
- `make db-up` - Start PostgreSQL database service (Docker Compose)
- `make migrate` - Run database migrations to latest version
- `make revision m="description"` - Create a new migration revision
- `make db-status` - Show current migration status
- `make db-rollback` - Rollback one migration

## Architecture

This project follows Clean Architecture principles with clear separation of concerns and dependency inversion.

### Layer Structure

```
app/
├── domain/              # Core business logic (innermost layer)
│   ├── entities/        # Domain entities
│   └── value_objects/   # Domain value objects
│
├── application/         # Application business logic
│   ├── use_cases/       # Application use cases
│   ├── dtos/            # Data Transfer Objects (Car, Chat, Financing, Lead, Knowledge)
│   └── ports/           # Interfaces (ports) for adapters
│
├── adapters/            # Adapters (implementations)
│   ├── inbound/         # Primary adapters (driving)
│   │   └── http/        # HTTP/FastAPI routes
│   └── outbound/        # Secondary adapters (driven)
│       ├── catalog/     # Car catalog adapter (CSV)
│       ├── knowledge_base/ # Knowledge base adapter (Markdown)
│       ├── idempotency/ # Idempotency store adapter (Redis)
│       ├── lead/        # Lead repository adapter (in-memory or postgres)
│       ├── state/       # Conversation state adapter (in-memory or postgres)
│       └── llm_rag/     # LLM/RAG adapter
│
├── infrastructure/      # Infrastructure concerns
│   ├── config/          # Configuration management
│   ├── db/              # Database setup (SQLAlchemy)
│   ├── logging/         # Logging setup
│   └── wiring/          # Dependency injection
│
└── main.py              # FastAPI entrypoint
```

### Dependency Rule

The fundamental rule of Clean Architecture is the **Dependency Rule**:

> **Source code dependencies can only point inward.**

This means:
- **Domain** (innermost) has no dependencies on other layers
- **Application** depends only on Domain
- **Adapters** depend on Application (ports) and Domain
- **Infrastructure** depends on Application and Domain
- **Main** wires everything together

### Dependency Flow

```
┌─────────────────────────────────────────┐
│         Infrastructure/Adapters         │  ← Outermost
│  (HTTP, CSV, LLM, Persistence, Config)  │
└──────────────┬──────────────────────────┘
               │ depends on
┌──────────────▼──────────────────────────┐
│           Application                    │
│  (Use Cases, DTOs, Ports/Interfaces)    │
└──────────────┬──────────────────────────┘
               │ depends on
┌──────────────▼──────────────────────────┐
│             Domain                       │  ← Innermost
│    (Entities, Value Objects)             │
└─────────────────────────────────────────┘
```

### Layer Responsibilities

#### Domain Layer
- Contains pure business logic
- No dependencies on frameworks or external libraries
- Defines core entities and value objects
- Business rules and domain logic

#### Application Layer
- Orchestrates use cases
- Defines ports (interfaces) that adapters must implement
- Contains DTOs for data transfer
- Application-specific business logic

#### Adapters Layer
- **Inbound (Primary)**: HTTP routes, CLI, message queues
- **Outbound (Secondary)**: Database, external APIs, file systems
- Implements ports defined in Application layer
- Translates between external world and application

#### Infrastructure Layer
- Cross-cutting concerns (config, logging)
- Dependency injection container
- Framework-specific setup

### Benefits

- **Testability**: Domain and application logic can be tested without external dependencies
- **Independence**: Business logic is independent of frameworks, databases, and UI
- **Flexibility**: Easy to swap adapters (e.g., change database, add new API)
- **Maintainability**: Clear boundaries make code easier to understand and modify

## Running the Application

### Docker (Recommended)

The easiest way to run the application is using Docker, which ensures consistent behavior across different environments.

#### Prerequisites

- Docker (Docker Desktop or Docker Engine)
- Docker Compose

#### Build and Run

```bash
docker-compose up --build
```

The application will be available at `http://localhost:8000`

**Endpoints:**
- API documentation: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`
- Chat endpoint: `POST http://localhost:8000/chat`
- WhatsApp webhook: `POST http://localhost:8000/channels/whatsapp/webhook`

See [Environment Variables](#environment-variables) for configuration options.

### Local Development (Python)

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Start the application:
   ```bash
   uvicorn app.main:app --reload
   ```

The application will be available at `http://localhost:8000`

### Database Setup (PostgreSQL)

The application supports PostgreSQL for persistent state storage. When using Docker Compose, the database service is automatically started.

**Local Setup:**
1. Start database: `make db-up`
2. Run migrations: `make migrate`
3. Set `CONVERSATION_STATE_REPOSITORY=postgres` and `DATABASE_URL` in environment

**Migration Commands:**
- `make migrate` - Apply all pending migrations
- `make revision m="description"` - Create a new migration
- `make db-status` - Show current migration status
- `make db-rollback` - Rollback one migration

### Debug Endpoints

When `DEBUG_MODE=true` is set, additional debug endpoints are available:
- `GET /debug/session/{session_id}` - Get conversation state for a session
- `POST /debug/session/{session_id}/reset` - Reset conversation state for a session
- `GET /debug/leads` - List all captured leads

**Note:** Debug endpoints are disabled by default for security reasons.

## Environment Variables

Feature flags are intentional design choices that enable deterministic behavior, safe rollouts, and easy demos. They allow swapping implementations without code changes, supporting both production reliability and development flexibility.

### Core

- `DEBUG_MODE` - Enable debug endpoints (default: `false`)

### Feature Flags

- `LLM_ENABLED` - Enable OpenAI LLM for natural language FAQ responses (default: `false`)
  - When enabled, FAQ responses use LLM for natural language generation
  - When disabled, uses deterministic text formatting from knowledge base
  - All responses are grounded in RAG to prevent hallucination

- `TWILIO_IDEMPOTENCY_ENABLED` - Enable Redis-based idempotency for webhook (default: `true`)
  - Prevents duplicate replies when Twilio retries webhook requests
  - Uses MessageSid for deduplication
  - Gracefully falls back to no-op if Redis unavailable

- `STATE_CACHE` - Enable Redis cache for conversation state (default: `none`, options: `none` or `redis`)
  - Uses cache-aside pattern: Redis as read cache, Postgres as source of truth
  - Reduces database queries on repeated session reads
  - State persists even if Redis unavailable

- `CONVERSATION_STATE_REPOSITORY` - State storage backend (default: `in_memory`, options: `in_memory` or `postgres`)
  - `in_memory`: State lost on restart (development/testing)
  - `postgres`: State persists across restarts (production)

- `LEAD_REPOSITORY` - Lead storage backend (default: `in_memory`, options: `in_memory` or `postgres`)
  - `in_memory`: Leads lost on restart (development/testing)
  - `postgres`: Leads persist across restarts (production)

### External Services

- `OPENAI_API_KEY` - OpenAI API key (required when `LLM_ENABLED=true`)
- `OPENAI_MODEL` - OpenAI model name (default: `gpt-4o-mini`)
- `OPENAI_TIMEOUT_SECONDS` - API timeout in seconds (default: `10`)

- `TWILIO_ACCOUNT_SID` - Twilio account SID (optional, for webhook)
- `TWILIO_AUTH_TOKEN` - Twilio auth token (optional, for webhook)
- `TWILIO_WHATSAPP_NUMBER` - Twilio WhatsApp number (optional)
- `TWILIO_VALIDATE_SIGNATURE` - Enable signature validation (default: `false`)

- `REDIS_URL` - Redis connection URL (default: `redis://localhost:6379/0`)
  - Used for idempotency when `TWILIO_IDEMPOTENCY_ENABLED=true`
  - Used for state caching when `STATE_CACHE=redis`

- `DATABASE_URL` - PostgreSQL connection string
  - Required when `CONVERSATION_STATE_REPOSITORY=postgres` or `LEAD_REPOSITORY=postgres`
  - Format: `postgresql+psycopg2://user:password@host:port/database`

### Additional Configuration

- `STATE_TTL_SECONDS` - Conversation state TTL in seconds (default: `86400` = 24 hours)
- `TWILIO_IDEMPOTENCY_TTL_SECONDS` - Idempotency TTL in seconds (default: `3600` = 1 hour)

**Configuration Notes:**
- For Docker Compose, create a `.env` file (see `.env.example`)
- For local development, pydantic-settings automatically loads `.env` or use shell environment variables
- Never commit `.env` to version control (it's in `.gitignore`)
