# TaskFlow API

TaskFlow API is a FastAPI-based backend service for managing tasks and user interactions. This API powers the TaskFlow dashboard application with features for task management, user authentication, and intelligent chat interactions.

## Features

- User management (create, retrieve users)
- Task management (create, read, update, delete, complete tasks)
- Intelligent chat endpoint for task interactions
- RESTful API design
- SQLite database integration

## Endpoints

### Health Check
- `GET /health` - Verify the service is running

### User Management
- `POST /users` - Create a new user
- `GET /users/{user_id}` - Get user details by ID

### Task Management
- `GET /api/{user_id}/tasks` - Get all tasks for a user
- `POST /api/{user_id}/tasks` - Create a new task
- `GET /api/{user_id}/tasks/{task_id}` - Get a specific task
- `PUT /api/{user_id}/tasks/{task_id}` - Update a task
- `DELETE /api/{user_id}/tasks/{task_id}` - Delete a task
- `PATCH /api/{user_id}/tasks/{task_id}/complete` - Toggle task completion

### Chat
- `POST /api/chat` - Process chat messages and provide intelligent responses

## Local Development

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the application:
   ```bash
   python main.py
   ```

The API will be available at `http://localhost:8080` (or the port specified by the PORT environment variable).

## Deployment

This application is designed for deployment on Railway. Simply connect your GitHub repository to Railway and it will automatically build and deploy the application.

## Technologies Used

- Python 3.11+
- FastAPI
- Uvicorn ASGI server
- SQLite for database
- Pydantic for data validation