from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import init_db
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    try:
        init_db()
    except Exception as e:
        print(f"Database connection failed (expected if DB not running yet): {e}")
    yield
    # Shutdown

app = FastAPI(title="Planner V2", lifespan=lifespan)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins (good for local dev)
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

from .routers import auth, manager, employee, scheduler
app.include_router(auth.router)
app.include_router(manager.router)
app.include_router(employee.router)
app.include_router(scheduler.router)

@app.get("/")
def read_root():
    return {"message": "Planner V2 API is running"}
# Reload trigger
