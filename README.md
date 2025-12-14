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

**WhatsApp webhook endpoint:**
```bash
curl -X POST http://localhost:8000/channels/whatsapp/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "From": "+521234567890",
    "Body": "Hola",
    "ProfileName": "Juan Pérez"
  }'
```

The webhook accepts Twilio-like payloads and maps them to the internal chat flow. The `From` field is used as the session ID, `Body` as the message, and `ProfileName` (optional) is stored in metadata.

**Run the demo script:**
```bash
chmod +x scripts/demo.sh
./scripts/demo.sh
```

The demo script simulates a full conversation flow in Spanish (need → budget → options → financing → lead capture).

## Features

- **Commercial Flow**: Guided conversation to understand customer needs, budget, preferences, and financing requirements
- **Car Catalog Search**: Search and recommend cars from CSV catalog based on customer criteria
- **Financing Calculator**: Calculate financing plans with multiple terms (36, 48, 60, 72 months)
- **FAQ RAG**: Answer frequently asked questions using Retrieval-Augmented Generation (RAG) from knowledge base
- **LLM-Powered Responses** (Optional): Natural language generation for FAQ responses using OpenAI, with deterministic fallback
- **Lead Capture**: Capture customer contact information (name, phone, preferred contact time) when they express purchase intent
- **WhatsApp Integration**: Webhook endpoint for Twilio/WhatsApp integration (`/channels/whatsapp/webhook`)
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
│       ├── lead/        # Lead repository adapter (in-memory)
│       ├── state/       # Conversation state adapter (in-memory or postgres)
│       └── llm_rag/     # LLM/RAG adapter
│
├── infrastructure/      # Infrastructure concerns
│   ├── config/          # Configuration management
│   ├── db/              # Database setup (SQLAlchemy)
│   ├── logging/        # Logging setup
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
- Docker Compose (optional, but recommended for easier environment variable management)

#### Build the Docker Image

```bash
docker build -t kavak-agent .
```

To use a different Python version:
```bash
docker build --build-arg PYTHON_VERSION=3.10 -t kavak-agent .
```

#### Run with Docker

**Basic run:**
```bash
docker run --rm -p 8000:8000 kavak-agent
```

**With environment variables:**
```bash
docker run --rm -p 8000:8000 \
  -e LLM_ENABLED=true \
  -e OPENAI_API_KEY=your_api_key_here \
  -e OPENAI_MODEL=gpt-4o-mini \
  -e DEBUG_MODE=false \
  -e TWILIO_ACCOUNT_SID=your_account_sid \
  -e TWILIO_AUTH_TOKEN=your_auth_token \
  -e TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886 \
  -e TWILIO_VALIDATE_SIGNATURE=false \
  kavak-agent
```

**Using docker-compose (recommended for development):**

1. Create a `.env` file with your configuration:
```bash
LLM_ENABLED=false
OPENAI_API_KEY=
DEBUG_MODE=false
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
# ... other variables
```

2. Run with docker-compose:
```bash
docker-compose up
```

The application will be available at `http://localhost:8000`

**Docker endpoints:**
- API documentation: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`
- Chat endpoint: `POST http://localhost:8000/chat`
- WhatsApp webhook: `POST http://localhost:8000/channels/whatsapp/webhook`

**Note:** When running in Docker, the WhatsApp webhook endpoint will need to be accessible from the internet (use a tunnel service like ngrok for local testing).

#### Docker Environment Variables

All environment variables can be passed to the container:

- `LLM_ENABLED` - Enable/disable LLM feature (default: `false`)
- `OPENAI_API_KEY` - OpenAI API key (required if `LLM_ENABLED=true`)
- `OPENAI_MODEL` - OpenAI model name (default: `gpt-4o-mini`)
- `OPENAI_TIMEOUT_SECONDS` - API timeout in seconds (default: `10`)
- `DEBUG_MODE` - Enable debug endpoints (default: `false`)
- `STATE_TTL_SECONDS` - Conversation state TTL (default: `86400`)
- `TWILIO_ACCOUNT_SID` - Twilio account SID (optional)
- `TWILIO_AUTH_TOKEN` - Twilio auth token (optional)
- `TWILIO_WHATSAPP_NUMBER` - Twilio WhatsApp number (optional)
- `TWILIO_VALIDATE_SIGNATURE` - Enable signature validation (default: `false`)
- `STATE_REPOSITORY` - State repository backend: `in_memory` (default) or `postgres`
- `DATABASE_URL` - PostgreSQL connection string (required when `STATE_REPOSITORY=postgres`)

### Database Setup (PostgreSQL)

The application supports two conversation state storage backends:

- **In-Memory** (default): State is stored in memory and lost on restart. Suitable for development and testing.
- **PostgreSQL**: State persists across restarts. Suitable for production.

#### Using PostgreSQL for State Persistence

1. **Start the PostgreSQL database:**
   ```bash
   make db-up
   # Or manually: docker compose up -d db
   ```

2. **Set environment variables:**
   ```bash
   export DATABASE_URL="postgresql+psycopg2://postgres:postgres@localhost:5432/kavak_agent"
   export STATE_REPOSITORY="postgres"
   ```

3. **Run database migrations:**
   ```bash
   make migrate
   # Or manually: alembic upgrade head
   ```

4. **Run the application:**
   ```bash
   make dev
   # Or: uvicorn app.main:app --reload
   ```

The application will now use PostgreSQL to persist conversation state across restarts.

**Note:** When using Docker Compose, the database service is automatically started and the `DATABASE_URL` is configured to connect to the `db` service. Set `STATE_REPOSITORY=postgres` in your `.env` file to enable PostgreSQL persistence.

**Migration Commands:**
- `make migrate` - Apply all pending migrations
- `make revision m="description"` - Create a new migration
- `make db-status` - Show current migration status
- `make db-rollback` - Rollback one migration

### Local Development (Python)

#### Prerequisites

- Python 3.9+
- pip

#### Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

#### Running with uvicorn

Start the FastAPI application using uvicorn:

```bash
uvicorn app.main:app --reload
```

The application will be available at `http://localhost:8000`

- API documentation: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`
- Chat endpoint: `POST http://localhost:8000/chat`
- WhatsApp webhook: `POST http://localhost:8000/channels/whatsapp/webhook`

### Debug Endpoints

When `DEBUG_MODE=true` is set in your environment, additional debug endpoints are available:

- `GET /debug/session/{session_id}` - Get conversation state for a session
- `POST /debug/session/{session_id}/reset` - Reset conversation state for a session
- `GET /debug/leads` - List all captured leads (requires DEBUG_MODE=true)

**Note:** Debug endpoints are disabled by default for security reasons. To enable them, set `DEBUG_MODE=true` in your environment variables (when using Docker Compose, use `.env` file).

### Running in production

**Using Docker (recommended):**
```bash
docker run -d \
  --name kavak-agent \
  -p 8000:8000 \
  -e LLM_ENABLED=true \
  -e OPENAI_API_KEY=${OPENAI_API_KEY} \
  -e DEBUG_MODE=false \
  --restart unless-stopped \
  kavak-agent
```

**Using uvicorn directly:**
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## Twilio WhatsApp Sandbox Setup

The application includes a webhook endpoint for Twilio WhatsApp integration. To connect your Twilio WhatsApp Sandbox:

### Prerequisites

1. A Twilio account with WhatsApp Sandbox access
2. A publicly reachable HTTPS URL for the webhook (use a tunnel for local development)

### Local Development Setup

For local development, you'll need to expose your local server using a tunnel service:

1. **Start the application:**
   ```bash
   make dev
   # Or: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

2. **Expose with a tunnel** (choose one):
   - **ngrok**: `ngrok http 8000`
   - **localtunnel**: `lt --port 8000`
   - **cloudflared**: `cloudflared tunnel --url http://localhost:8000`

3. **Copy the HTTPS URL** from your tunnel (e.g., `https://abc123.ngrok.io`)

### Twilio Console Configuration

1. **Log in to Twilio Console**: https://console.twilio.com

2. **Navigate to WhatsApp Sandbox**:
   - Go to **Messaging** → **Try it out** → **Send a WhatsApp message**
   - Or navigate to **Messaging** → **Settings** → **WhatsApp Sandbox**

3. **Configure Webhook URL**:
   - In the "When a message comes in" field, enter:
     ```
     https://your-tunnel-url.ngrok.io/channels/whatsapp/webhook
     ```
   - Replace `your-tunnel-url.ngrok.io` with your actual tunnel URL
   - Set HTTP method to **POST**
   - Click **Save**

4. **Test the Integration**:
   - Send a WhatsApp message to your Twilio Sandbox number (shown in the console)
   - The bot should respond in Spanish

### Environment Variables

### Environment Variables

**For Docker Compose:** Create a `.env` file in the project root (Docker Compose will automatically load it). Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

**For local Python development:** You can either:
- Use a `.env` file (pydantic-settings will automatically load it)
- Set environment variables in your shell: `export LLM_ENABLED=true`
- Pass variables when running: `LLM_ENABLED=true uvicorn app.main:app --reload`

**Note:** The `.env` file is primarily used by Docker Compose, but pydantic-settings will also read it for local development if present.

Required/optional environment variables:

```bash
# Application Configuration
DEBUG_MODE=false
STATE_TTL_SECONDS=86400

# Twilio Configuration
# Get these from your Twilio Console: https://console.twilio.com
TWILIO_ACCOUNT_SID=your_account_sid_here
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886

# Enable signature validation (default: false)
TWILIO_VALIDATE_SIGNATURE=false

# OpenAI LLM Configuration (Optional)
# Enable LLM-powered natural language generation for FAQ responses
LLM_ENABLED=false
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o-mini
OPENAI_TIMEOUT_SECONDS=10
```

**Note**: 
- Signature validation is disabled by default for local development. Enable it in production for security.
- Never commit `.env` to version control (it's in `.gitignore`).
- The `.env.example` file shows all available configuration options.
- LLM feature is disabled by default. Set `LLM_ENABLED=true` to enable OpenAI-powered responses.
- The `.env` file is automatically loaded by Docker Compose. For local Python development, pydantic-settings will also read it, or you can set environment variables in your shell.

### Webhook Endpoint Details

- **Endpoint**: `POST /channels/whatsapp/webhook`
- **Content-Type**: `application/x-www-form-urlencoded` (Twilio sends form data)
- **Response**: TwiML XML (`application/xml`)
- **Required Fields**: `From`, `Body`
- **Optional Fields**: `ProfileName`, `MessageSid`

The webhook accepts Twilio's form-encoded payload and returns TwiML XML with the Spanish reply generated by the agent.

## OpenAI LLM Integration (Optional)

The application includes an optional OpenAI LLM integration that can generate natural language responses for FAQ questions. The LLM is used only for response generation, while factual content is always grounded in the knowledge base through RAG to prevent hallucination.

### Features

- **Natural Language Generation**: The LLM rephrases retrieved knowledge base chunks into natural, conversational Spanish responses
- **Deterministic Fallback**: If the LLM is disabled, unavailable, or fails, the system automatically falls back to deterministic text formatting
- **RAG Grounding**: All LLM responses are grounded in retrieved knowledge base chunks to ensure factual accuracy
- **Spanish-Only Output**: The LLM is explicitly instructed to respond only in Spanish

### Configuration

To enable the LLM feature, set the following environment variables (in `.env` file for Docker Compose, or in your shell environment for local development):

```bash
# Enable LLM feature
LLM_ENABLED=true

# OpenAI API key (required when LLM_ENABLED=true)
OPENAI_API_KEY=sk-...

# OpenAI model (optional, defaults to gpt-4o-mini)
OPENAI_MODEL=gpt-4o-mini

# Request timeout in seconds (optional, defaults to 10)
OPENAI_TIMEOUT_SECONDS=10
```

### How It Works

1. **When LLM is enabled** (`LLM_ENABLED=true`):
   - FAQ questions trigger RAG retrieval from the knowledge base
   - Retrieved chunks are passed to the LLM with strict instructions to:
     - Respond only in Spanish
     - Use only information from the provided context
     - Not add any facts not in the knowledge base
   - The LLM generates a natural Spanish response based on the retrieved content

2. **When LLM is disabled** (`LLM_ENABLED=false` or missing):
   - The system uses deterministic text formatting
   - Responses are extracted directly from knowledge base chunks
   - This ensures consistent, predictable behavior

3. **Error Handling**:
   - If the LLM API call fails or returns empty, the system automatically falls back to deterministic formatting
   - No user-facing errors are shown; the fallback is seamless

### Usage

The LLM integration is transparent to the user. When enabled, FAQ responses will be more natural and conversational while maintaining factual accuracy. When disabled (default), responses use deterministic formatting for consistency.

**Example FAQ flow with LLM enabled:**

1. User asks: "¿Qué garantías ofrecen?"
2. System retrieves relevant chunks from knowledge base
3. LLM generates: "En Kavak ofrecemos una garantía de 3 meses que puedes extender hasta 1 año. Además, tienes 7 días o 300 km de prueba..."
4. Response is returned in Spanish

**Example FAQ flow with LLM disabled:**

1. User asks: "¿Qué garantías ofrecen?"
2. System retrieves relevant chunks from knowledge base
3. System formats chunk text directly: "## 8. Periodo de Prueba y Garantía\n\n* **Garantía de 3 meses**, con opción de extender hasta 1 año..."
4. Response is returned in Spanish

