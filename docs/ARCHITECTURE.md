# Zentar Intelligence — Architecture Document

## Overview
Zentar Intelligence is a production-ready Android AI assistant with a Railway-hosted backend combining personal assistance, coding agent capabilities, automation, and a plugin ecosystem.

## System Architecture

```
┌─────────────────────────────────────────────────────┐
│                   Android App                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐   │
│  │   UI     │  │  ViewModel│  │   Repository     │   │
│  │ Compose  │◄─┤    Layer  │◄─┤     Layer        │   │
│  └──────────┘  └──────────┘  └───────┬──────────┘   │
│                                       │              │
│  ┌────────────────────────────────────┴──────────┐  │
│  │           Network / Local Data                │  │
│  │  Retrofit + OkHttp │ Room DB │ DataStore      │  │
│  └───────────────────────────────────────────────┘  │
└──────────────────────┬──────────────────────────────┘
                       │ HTTPS / WebSocket
┌──────────────────────┴──────────────────────────────┐
│               Railway Backend                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐   │
│  │ REST API │  │WebSocket │  │  AI Agent Engine │   │
│  │FastAPI   │  │  Handler │  │                  │   │
│  └────┬─────┘  └────┬─────┘  └───────┬──────────┘   │
│       │              │                │              │
│  ┌────┴──────────────┴────────────────┴──────────┐  │
│  │              Core Services                     │  │
│  │  Auth │ MCP │ Plugins │ Skills │ Memory │      │  │
│  └───────────────────────────────────────────────┘  │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐   │
│  │PostgreSQL│  │  Redis   │  │  Background       │   │
│  │          │  │          │  │  Workers (Celery) │   │
│  └──────────┘  └──────────┘  └──────────────────┘   │
└─────────────────────────────────────────────────────┘
```

## Technology Stack

### Backend
- **Framework**: FastAPI (Python 3.11+)
- **Database**: PostgreSQL (SQLAlchemy ORM + Alembic)
- **Cache**: Redis (caching, rate limiting, pub/sub)
- **Auth**: JWT (access + refresh tokens), OAuth2
- **Workers**: Background tasks via asyncio + Redis queue
- **Deployment**: Railway + Docker

### Android
- **Language**: Kotlin
- **UI**: Jetpack Compose + Material 3
- **Architecture**: MVVM + Clean Architecture
- **DI**: Hilt
- **Network**: Retrofit + OkHttp
- **Local**: Room DB + DataStore
- **WebSocket**: OkHttp WebSocket
- **Async**: Kotlin Coroutines + Flow

## Core Modules

### 1. Authentication Module
- JWT-based with refresh tokens
- OAuth2 provider support (Google, GitHub)
- Biometric auth on device
- Session management

### 2. AI Agent Engine
- Multi-provider support (OpenAI, Gemini, Claude, DeepSeek, Qwen, Ollama, OpenRouter)
- Model routing with failover
- Streaming responses via Server-Sent Events
- Conversation context management
- Prompt templating system

### 3. MCP (Model Context Protocol)
- MCP client implementation
- Server registry and management
- Tool, resource, prompt discovery
- OAuth and token authentication for servers
- Auto-reconnect with exponential backoff

### 4. Plugin System
- Plugin lifecycle management (install, enable, disable, uninstall)
- Sandboxed execution environment
- Permission model
- Event-based communication
- Hot-reload support
- Marketplace integration

### 5. Skills System
- Skill definitions with prompts, tools, and memory
- Version management and dependencies
- Installable from marketplace or custom URLs
- Permission scoping per skill

### 6. Memory System
- Conversation memory (short-term)
- Long-term memory with semantic search
- Project-scoped memory
- Pinned memories
- Custom notes

### 7. Android Automation
- Accessibility Service for UI interaction
- Notification Listener for event capture
- WorkManager for task scheduling
- Voice command processing
- File system operations

### 8. Coding Agent
- Project workspace management
- File editor with syntax highlighting
- Git integration
- Code analysis and review
- Bug detection and fixing
- Code generation

### 9. Web Features
- Web search integration
- Content extraction and summarization
- Research mode with source tracking
- File download management

### 10. Voice Assistant
- Speech-to-text (on-device + cloud)
- Text-to-speech
- Wake word detection
- Continuous conversation mode

## Data Flow

```
User Input → UI → ViewModel → Repository → API/WebSocket → Backend
                                                              │
                                                    AI Provider (routed)
                                                              │
User ← UI ← ViewModel ← Repository ← API/WebSocket ← Response (streamed)
```

## Security Architecture
- All traffic over HTTPS/WSS
- JWT tokens with short expiry (15min access, 7d refresh)
- Encrypted local storage (Android Keystore)
- API key management with encryption at rest
- Rate limiting via Redis sliding window
- Plugin sandboxing with resource limits
- Audit logging for sensitive operations

## Database Schema (Core Tables)
- users
- conversations
- messages
- models
- providers
- plugins
- skills
- memories
- api_keys
- audit_logs
- sessions
- automation_rules

## API Structure
```
/api/v1/
├── auth/           # Authentication endpoints
├── chat/           # Chat and conversation management
├── agents/         # AI agent configuration
├── models/         # Model management
├── providers/      # Provider configuration
├── mcp/            # MCP server management
├── plugins/        # Plugin system
├── skills/         # Skills system
├── memory/         # Memory management
├── files/          # File operations
├── automation/     # Automation rules
├── admin/          # Admin panel
└── web/            # Web search and research
```

## Deployment Architecture
```
GitHub → Railway (Docker container)
         ├── Web service (FastAPI)
         ├── PostgreSQL
         └── Redis
```

## Development Phases

### Phase 1: Foundation
- [x] Project scaffolding
- [x] Architecture document
- [ ] Backend core (auth, database, base models)
- [ ] Android scaffold (navigation, theme, core UI)

### Phase 2: AI Engine
- [ ] AI provider integrations
- [ ] Chat system
- [ ] Streaming responses
- [ ] Conversation management

### Phase 3: MCP & Plugins
- [ ] MCP protocol implementation
- [ ] Plugin system
- [ ] Skills system
- [ ] Marketplace

### Phase 4: Advanced Features
- [ ] Coding agent
- [ ] Android automation
- [ ] Voice assistant
- [ ] Memory system

### Phase 5: Polish & Deploy
- [ ] Testing
- [ ] Security audit
- [ ] Performance optimization
- [ ] Railway deployment
- [ ] CI/CD pipeline
