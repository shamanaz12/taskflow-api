from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import uuid
import sqlite3
import os
import json

# Initialize FastAPI app with documentation
app = FastAPI(
    title="TaskFlow API",
    description="Complete API for TaskFlow application with task management and chat functionality",
    version="1.0.0",
    docs_url="/docs",  # Enable Swagger documentation
    redoc_url="/redoc"  # Enable ReDoc documentation
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database setup
DB_PATH = "taskflow.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create tasks table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT,
            completed BOOLEAN DEFAULT 0,
            user_id TEXT NOT NULL,
            priority INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()

# Initialize database
init_db()

# Pydantic models
class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    completed: bool = False
    priority: int = 1  # 0: low, 1: medium, 2: high

class TaskCreate(TaskBase):
    user_id: str

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    completed: Optional[bool] = None
    priority: Optional[int] = None

class Task(TaskBase):
    id: str
    user_id: str
    created_at: datetime
    updated_at: datetime

class User(BaseModel):
    id: str
    name: str
    email: str
    created_at: datetime

class ChatRequest(BaseModel):
    message: str
    user_id: str

class ChatResponse(BaseModel):
    response: str
    action_taken: Optional[str] = None
    suggested_action: Optional[str] = None

class HealthCheck(BaseModel):
    status: str
    timestamp: datetime
    service: str = "TaskFlow API"

# Helper functions
def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = dict_factory
    return conn

# API Endpoints Documentation:
#
# 1. HEALTH CHECK ENDPOINT
#    GET /health
#    Request: None
#    Response: {"status": "healthy", "timestamp": "2023-01-01T00:00:00Z", "service": "TaskFlow API"}
#
# 2. USER MANAGEMENT ENDPOINTS
#    POST /users - Create a new user
#    Request: {"name": "John Doe", "email": "john@example.com"}
#    Response: {"id": "uuid", "name": "John Doe", "email": "john@example.com", "created_at": "timestamp"}
#
#    GET /users/{user_id} - Get user by ID
#    Request: None
#    Response: {"id": "uuid", "name": "John Doe", "email": "john@example.com", "created_at": "timestamp"}
#
# 3. TASK MANAGEMENT ENDPOINTS
#    GET /api/{user_id}/tasks - Get all tasks for a user
#    Request: None
#    Response: [{"id": "uuid", "title": "Task 1", "description": "Desc", "completed": false, "priority": 1, "user_id": "uuid", "created_at": "timestamp", "updated_at": "timestamp"}]
#
#    POST /api/{user_id}/tasks - Create a new task
#    Request: {"title": "New Task", "description": "Task description", "completed": false, "priority": 1}
#    Response: {"id": "uuid", "title": "New Task", "description": "Task description", "completed": false, "priority": 1, "user_id": "uuid", "created_at": "timestamp", "updated_at": "timestamp"}
#
#    GET /api/{user_id}/tasks/{task_id} - Get a specific task
#    Request: None
#    Response: {"id": "uuid", "title": "Task 1", "description": "Desc", "completed": false, "priority": 1, "user_id": "uuid", "created_at": "timestamp", "updated_at": "timestamp"}
#
#    PUT /api/{user_id}/tasks/{task_id} - Update a task
#    Request: {"title": "Updated Task", "description": "Updated desc", "completed": true, "priority": 2}
#    Response: {"id": "uuid", "title": "Updated Task", "description": "Updated desc", "completed": true, "priority": 2, "user_id": "uuid", "created_at": "timestamp", "updated_at": "timestamp"}
#
#    DELETE /api/{user_id}/tasks/{task_id} - Delete a task
#    Request: None
#    Response: {"message": "Task deleted successfully"}
#
#    PATCH /api/{user_id}/tasks/{task_id}/complete - Toggle task completion
#    Request: None
#    Response: {"id": "uuid", "title": "Task 1", "description": "Desc", "completed": true, "priority": 1, "user_id": "uuid", "created_at": "timestamp", "updated_at": "timestamp"}
#
# 4. CHAT ENDPOINT
#    POST /api/chat - Process chat message
#    Request: {"message": "Add a new task to buy groceries", "user_id": "uuid"}
#    Response: {"response": "I'll help you add a task...", "action_taken": "suggest_create_task", "suggested_action": "create_task_form"}

# Health check endpoint
@app.get("/health", response_model=HealthCheck)
def health_check():
    """
    Health check endpoint to verify the service is running
    """
    return HealthCheck(
        status="healthy",
        timestamp=datetime.utcnow(),
        service="TaskFlow API"
    )

# User creation endpoint
class UserCreate(BaseModel):
    name: str
    email: str

@app.post("/users", response_model=User)
def create_user(user_data: UserCreate):
    """
    Create a new user in the system
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    user_id = str(uuid.uuid4())
    try:
        cursor.execute('''
            INSERT INTO users (id, name, email)
            VALUES (?, ?, ?)
        ''', (user_id, user_data.name, user_data.email))

        conn.commit()
        conn.close()

        # Return the created user
        created_user = {
            'id': user_id,
            'name': user_data.name,
            'email': user_data.email,
            'created_at': datetime.utcnow()
        }

        return User(**created_user)
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=400, detail="Email already registered")

@app.get("/users/{user_id}", response_model=User)
def get_user(user_id: str):
    """
    Get user details by ID
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()

    conn.close()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user['created_at'] = datetime.fromisoformat(user['created_at']) if isinstance(user['created_at'], str) else user['created_at']
    return User(**user)

# Task endpoints
@app.post("/api/{user_id}/tasks", response_model=Task)
def create_task(user_id: str, task: TaskCreate):
    """
    Create a new task for a specific user
    """
    # Verify user exists
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT id FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    if not user:
        conn.close()
        raise HTTPException(status_code=404, detail="User not found")

    task_id = str(uuid.uuid4())
    cursor.execute('''
        INSERT INTO tasks (id, title, description, completed, user_id, priority)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (task_id, task.title, task.description, task.completed, task.user_id, task.priority))

    conn.commit()
    conn.close()

    # Return the created task
    created_task = task.dict()
    created_task['id'] = task_id
    created_task['created_at'] = datetime.utcnow()
    created_task['updated_at'] = datetime.utcnow()

    return Task(**created_task)

@app.get("/api/{user_id}/tasks", response_model=List[Task])
def get_tasks(user_id: str):
    """
    Get all tasks for a specific user
    """
    # Verify user exists
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT id FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    if not user:
        conn.close()
        raise HTTPException(status_code=404, detail="User not found")

    cursor.execute('SELECT * FROM tasks WHERE user_id = ?', (user_id,))
    tasks = cursor.fetchall()

    conn.close()

    # Convert to Task objects
    task_objects = []
    for task in tasks:
        task['created_at'] = datetime.fromisoformat(task['created_at']) if isinstance(task['created_at'], str) else task['created_at']
        task['updated_at'] = datetime.fromisoformat(task['updated_at']) if isinstance(task['updated_at'], str) else task['updated_at']
        task_objects.append(Task(**task))

    return task_objects

@app.get("/api/{user_id}/tasks/{task_id}", response_model=Task)
def get_task(user_id: str, task_id: str):
    """
    Get a specific task by ID for a specific user
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT id FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    if not user:
        conn.close()
        raise HTTPException(status_code=404, detail="User not found")

    cursor.execute('SELECT * FROM tasks WHERE id = ? AND user_id = ?', (task_id, user_id))
    task = cursor.fetchone()

    conn.close()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    task['created_at'] = datetime.fromisoformat(task['created_at']) if isinstance(task['created_at'], str) else task['created_at']
    task['updated_at'] = datetime.fromisoformat(task['updated_at']) if isinstance(task['updated_at'], str) else task['updated_at']

    return Task(**task)

@app.put("/api/{user_id}/tasks/{task_id}", response_model=Task)
def update_task(user_id: str, task_id: str, task_update: TaskUpdate):
    """
    Update a specific task by ID for a specific user
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Verify user exists
    cursor.execute('SELECT id FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    if not user:
        conn.close()
        raise HTTPException(status_code=404, detail="User not found")

    # Get current task
    cursor.execute('SELECT * FROM tasks WHERE id = ? AND user_id = ?', (task_id, user_id))
    current_task = cursor.fetchone()

    if not current_task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Update fields
    update_fields = {}
    for field, value in task_update.dict(exclude_unset=True).items():
        if value is not None:
            update_fields[field] = value

    # Build update query
    if update_fields:
        set_clause = ", ".join([f"{field} = ?" for field in update_fields.keys()])
        values = list(update_fields.values()) + [task_id, user_id]

        cursor.execute(f'''
            UPDATE tasks
            SET {set_clause}, updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND user_id = ?
        ''', values)

    conn.commit()
    conn.close()

    # Return updated task
    cursor.execute('SELECT * FROM tasks WHERE id = ? AND user_id = ?', (task_id, user_id))
    updated_task = cursor.fetchone()

    updated_task['created_at'] = datetime.fromisoformat(updated_task['created_at']) if isinstance(updated_task['created_at'], str) else updated_task['created_at']
    updated_task['updated_at'] = datetime.fromisoformat(updated_task['updated_at']) if isinstance(updated_task['updated_at'], str) else updated_task['updated_at']

    return Task(**updated_task)

@app.delete("/api/{user_id}/tasks/{task_id}")
def delete_task(user_id: str, task_id: str):
    """
    Delete a specific task by ID for a specific user
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Verify user exists
    cursor.execute('SELECT id FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    if not user:
        conn.close()
        raise HTTPException(status_code=404, detail="User not found")

    cursor.execute('SELECT * FROM tasks WHERE id = ? AND user_id = ?', (task_id, user_id))
    task = cursor.fetchone()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    cursor.execute('DELETE FROM tasks WHERE id = ? AND user_id = ?', (task_id, user_id))
    conn.commit()
    conn.close()

    return {"message": "Task deleted successfully"}

@app.patch("/api/{user_id}/tasks/{task_id}/complete", response_model=Task)
def toggle_task_completion(user_id: str, task_id: str):
    """
    Toggle the completion status of a specific task
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Verify user exists
    cursor.execute('SELECT id FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    if not user:
        conn.close()
        raise HTTPException(status_code=404, detail="User not found")

    cursor.execute('SELECT * FROM tasks WHERE id = ? AND user_id = ?', (task_id, user_id))
    task = cursor.fetchone()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Toggle completion status
    new_completed_status = not bool(task['completed'])
    cursor.execute('''
        UPDATE tasks
        SET completed = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ? AND user_id = ?
    ''', (new_completed_status, task_id, user_id))

    conn.commit()
    conn.close()

    # Return updated task
    cursor.execute('SELECT * FROM tasks WHERE id = ? AND user_id = ?', (task_id, user_id))
    updated_task = cursor.fetchone()

    updated_task['created_at'] = datetime.fromisoformat(updated_task['created_at']) if isinstance(updated_task['created_at'], str) else updated_task['created_at']
    updated_task['updated_at'] = datetime.fromisoformat(updated_task['updated_at']) if isinstance(updated_task['updated_at'], str) else updated_task['updated_at']

    return Task(**updated_task)

# Chat endpoint
@app.post("/api/chat", response_model=ChatResponse)
def chat_endpoint(request: ChatRequest):
    """
    Process chat messages and provide intelligent responses
    """
    message = request.message.lower()
    user_id = request.user_id

    # Verify user exists
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT id FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    if not user:
        conn.close()
        raise HTTPException(status_code=404, detail="User not found")

    conn.close()

    # Simple rule-based responses for task management
    if any(word in message for word in ["add", "create", "new", "task", "todo"]):
        return ChatResponse(
            response=f"I can help you add a task. Please use the task form in the dashboard to create: '{request.message}'",
            action_taken="suggest_create_task",
            suggested_action="create_task_form"
        )
    elif any(word in message for word in ["show", "list", "see", "my", "tasks", "todos"]):
        return ChatResponse(
            response="I can help you view your tasks. Your tasks are displayed in the dashboard.",
            action_taken="suggest_view_tasks",
            suggested_action="navigate_to_dashboard"
        )
    elif any(word in message for word in ["complete", "done", "finish", "mark"]):
        return ChatResponse(
            response=f"I can help you mark a task as complete. You can click the checkbox next to any task in the dashboard to mark it as complete.",
            action_taken="suggest_complete_task",
            suggested_action="click_task_checkbox"
        )
    elif any(word in message for word in ["delete", "remove", "cancel"]):
        return ChatResponse(
            response=f"I can help you delete a task. You can remove tasks using the delete button in the dashboard.",
            action_taken="suggest_delete_task",
            suggested_action="click_delete_button"
        )
    elif any(word in message for word in ["hello", "hi", "hey", "help"]):
        return ChatResponse(
            response="Hello! I'm your TaskFlow assistant. I can help you manage your tasks. Try saying 'add a task', 'show my tasks', or 'mark task as complete'.",
            action_taken="provide_assistance",
            suggested_action="show_help_menu"
        )
    else:
        return ChatResponse(
            response=f"I received your message: '{request.message}'. I'm here to help you manage your tasks. Try commands like 'add a task', 'show my tasks', or 'mark task as complete'.",
            action_taken="acknowledge_message",
            suggested_action="show_available_commands"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)