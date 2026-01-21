from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import uuid
import os
import psycopg2
from psycopg2.extras import RealDictCursor

# Initialize FastAPI app
app = FastAPI(
    title="TaskFlow API",
    description="Complete API for TaskFlow with Neon PostgreSQL",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Neon PostgreSQL Database URL
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://neondb_owner:npg_3PpKacOl8ysd@ep-little-fire-ahtqcsxh-pooler.c-3.us-east-1.aws.neon.tech/neondb?sslmode=require")

def get_db_connection():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT NOW()
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT,
            completed BOOLEAN DEFAULT false,
            user_id TEXT NOT NULL,
            priority INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    ''')

    conn.commit()
    cursor.close()
    conn.close()

# Initialize database on startup
init_db()

# Pydantic models
class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    completed: bool = False
    priority: int = 1

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

class UserCreate(BaseModel):
    name: str
    email: str

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

# Root endpoint
@app.get("/")
def root():
    return {"message": "TaskFlow API is running!", "status": "healthy", "version": "1.0.0", "docs": "/docs"}

@app.get("/health")
def health():
    return {"status": "healthy", "version": "1.0.0"}

# User endpoints
@app.post("/users", response_model=User)
def create_user(user_data: UserCreate):
    conn = get_db_connection()
    cursor = conn.cursor()

    user_id = str(uuid.uuid4())
    try:
        cursor.execute(
            'INSERT INTO users (id, name, email) VALUES (%s, %s, %s) RETURNING *',
            (user_id, user_data.name, user_data.email)
        )
        user = cursor.fetchone()
        conn.commit()
        cursor.close()
        conn.close()
        return User(**user)
    except psycopg2.IntegrityError:
        conn.rollback()
        cursor.close()
        conn.close()
        raise HTTPException(status_code=400, detail="Email already registered")

@app.get("/users/{user_id}", response_model=User)
def get_user(user_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))
    user = cursor.fetchone()

    cursor.close()
    conn.close()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return User(**user)

# Task endpoints
@app.get("/api/{user_id}/tasks", response_model=List[Task])
def get_tasks(user_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM tasks WHERE user_id = %s ORDER BY created_at DESC', (user_id,))
    tasks = cursor.fetchall()

    cursor.close()
    conn.close()

    return [Task(**task) for task in tasks]

@app.post("/api/{user_id}/tasks", response_model=Task)
def create_task(user_id: str, task: TaskBase):
    conn = get_db_connection()
    cursor = conn.cursor()

    task_id = str(uuid.uuid4())
    cursor.execute(
        '''INSERT INTO tasks (id, title, description, completed, user_id, priority)
           VALUES (%s, %s, %s, %s, %s, %s) RETURNING *''',
        (task_id, task.title, task.description, task.completed, user_id, task.priority)
    )
    new_task = cursor.fetchone()
    conn.commit()
    cursor.close()
    conn.close()

    return Task(**new_task)

@app.get("/api/{user_id}/tasks/{task_id}", response_model=Task)
def get_task(user_id: str, task_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM tasks WHERE id = %s AND user_id = %s', (task_id, user_id))
    task = cursor.fetchone()

    cursor.close()
    conn.close()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return Task(**task)

@app.put("/api/{user_id}/tasks/{task_id}", response_model=Task)
def update_task(user_id: str, task_id: str, task_update: TaskUpdate):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Get current task
    cursor.execute('SELECT * FROM tasks WHERE id = %s AND user_id = %s', (task_id, user_id))
    existing_task = cursor.fetchone()

    if not existing_task:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Task not found")

    # Update fields
    title = task_update.title if task_update.title is not None else existing_task['title']
    description = task_update.description if task_update.description is not None else existing_task['description']
    completed = task_update.completed if task_update.completed is not None else existing_task['completed']
    priority = task_update.priority if task_update.priority is not None else existing_task['priority']

    cursor.execute(
        '''UPDATE tasks SET title = %s, description = %s, completed = %s, priority = %s, updated_at = NOW()
           WHERE id = %s AND user_id = %s RETURNING *''',
        (title, description, completed, priority, task_id, user_id)
    )
    updated_task = cursor.fetchone()
    conn.commit()
    cursor.close()
    conn.close()

    return Task(**updated_task)

@app.delete("/api/{user_id}/tasks/{task_id}")
def delete_task(user_id: str, task_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('DELETE FROM tasks WHERE id = %s AND user_id = %s RETURNING id', (task_id, user_id))
    deleted = cursor.fetchone()
    conn.commit()
    cursor.close()
    conn.close()

    if not deleted:
        raise HTTPException(status_code=404, detail="Task not found")

    return {"message": "Task deleted successfully"}

# Chat endpoint
@app.post("/api/chat", response_model=ChatResponse)
def chat_endpoint(request: ChatRequest):
    message = request.message.lower()

    if any(word in message for word in ["add", "create", "new"]):
        return ChatResponse(
            response=f"I'll help you create a task. Use the task form in dashboard.",
            action_taken="suggest_create_task",
            suggested_action="create_task_form"
        )
    elif any(word in message for word in ["show", "list", "tasks"]):
        return ChatResponse(
            response="Your tasks are displayed in the dashboard.",
            action_taken="suggest_view_tasks",
            suggested_action="navigate_to_dashboard"
        )
    elif any(word in message for word in ["complete", "done", "finish"]):
        return ChatResponse(
            response="Click the checkbox next to any task to mark it complete.",
            action_taken="suggest_complete_task",
            suggested_action="click_task_checkbox"
        )
    elif any(word in message for word in ["delete", "remove"]):
        return ChatResponse(
            response="Use the delete button in the dashboard to remove tasks.",
            action_taken="suggest_delete_task",
            suggested_action="click_delete_button"
        )
    elif any(word in message for word in ["hello", "hi", "help"]):
        return ChatResponse(
            response="Hello! I'm TaskFlow assistant. Try: 'add task', 'show tasks', 'complete task'",
            action_taken="provide_assistance",
            suggested_action="show_help_menu"
        )
    else:
        return ChatResponse(
            response=f"I received: '{request.message}'. Try: 'add task', 'show tasks', or 'help'",
            action_taken="acknowledge_message",
            suggested_action="show_available_commands"
        )

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, log_level="info")
