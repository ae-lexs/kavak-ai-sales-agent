# Kavak AI Sales Agent

AI-powered sales agent built with FastAPI using Clean Architecture (Ports & Adapters pattern).

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
│   ├── dtos/            # Data Transfer Objects
│   └── ports/           # Interfaces (ports) for adapters
│
├── adapters/            # Adapters (implementations)
│   ├── inbound/         # Primary adapters (driving)
│   │   └── http/        # HTTP/FastAPI routes
│   └── outbound/        # Secondary adapters (driven)
│       ├── catalog_csv/ # CSV catalog adapter
│       ├── llm_rag/     # LLM/RAG adapter
│       └── persistence/ # Database/persistence adapter
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

