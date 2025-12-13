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
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
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
│       ├── state/       # Conversation state adapter (in-memory)
│       └── llm_rag/     # LLM/RAG adapter
│
├── infrastructure/      # Infrastructure concerns
│   ├── config/          # Configuration management
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

### Prerequisites

- Python 3.9+
- pip

### Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

### Running with uvicorn

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

**Note:** Debug endpoints are disabled by default for security reasons. To enable them, set `DEBUG_MODE=true` in your environment or `.env` file.

### Running in production

For production, use uvicorn with appropriate workers:

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

Optional environment variables for Twilio integration:

```bash
# Twilio Auth Token (for signature validation)
TWILIO_AUTH_TOKEN=your_auth_token_here

# Enable signature validation (default: false)
TWILIO_VALIDATE_SIGNATURE=true
```

**Note**: Signature validation is disabled by default for local development. Enable it in production for security.

### Webhook Endpoint Details

- **Endpoint**: `POST /channels/whatsapp/webhook`
- **Content-Type**: `application/x-www-form-urlencoded` (Twilio sends form data)
- **Response**: TwiML XML (`application/xml`)
- **Required Fields**: `From`, `Body`
- **Optional Fields**: `ProfileName`, `MessageSid`

The webhook accepts Twilio's form-encoded payload and returns TwiML XML with the Spanish reply generated by the agent.

