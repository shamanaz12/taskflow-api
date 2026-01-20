# TaskFlow API - Hackathon 2 Phase 3
FastAPI + Neon PostgreSQL backend

## Endpoints
- GET /tasks           → List tasks
- POST /tasks          → Create task
- PUT /tasks/{id}      → Toggle complete
- DELETE /tasks/{id}   → Delete task
- POST /chat           → AI Agent chat

## Test
```bash
curl -X POST {YOUR_RAILWAY_URL}/tasks -H "Content-Type: application/json" -d '{"title":"Test task"}'
```