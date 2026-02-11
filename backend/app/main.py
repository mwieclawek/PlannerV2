from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    from .database import init_db, DATABASE_URL
    
    # For local SQLite development AND Jenkins test environment.
    # In a full production env with migrations, this might be redundant but is generally safe 
    # as create_all checks for existence.
    logger.info(f"Initializing database structure (URL starts with: {DATABASE_URL[:10]}...)...")
    init_db()
    
    logger.info("Application startup complete. Database ready.")
    yield
    # Shutdown
    logger.info("Application shutdown.")

app = FastAPI(title="Planner V2", lifespan=lifespan)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:5000",
        "http://127.0.0.1:5000",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
