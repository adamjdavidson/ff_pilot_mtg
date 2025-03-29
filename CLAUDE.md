# AI Meeting Assistant Developer Guidelines

## Build & Run Commands
- Backend: `uvicorn main:app --host 0.0.0.0 --port 8080 --reload`
- Deploy: `docker build -t ai-meeting-assistant ./backend && docker run -p 8080:8080 ai-meeting-assistant`
- Frontend: Firebase hosting (use Firebase CLI)

## Style Guidelines
### Python (Backend)
- Imports: Standard library → Third-party → Local modules
- Type hints: Use for function signatures and complex data structures
- Naming: `snake_case` for variables/functions, `PascalCase` for classes
- Error handling: Use try/except with specific exceptions, proper logging
- Async: Use async/await patterns consistently

### JavaScript (Frontend)
- ES6+ syntax with async/await pattern
- `camelCase` for variables/functions
- Resource cleanup in event handlers
- Clear function naming (verb+noun pattern)

## Architecture Guidelines
- Agent system: Specialized AI agents in `backend/agents/`
- Traffic Cop pattern for routing logic between agents
- WebSocket for real-time communication
- Comprehensive error handling and logging