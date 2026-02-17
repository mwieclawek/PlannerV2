from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import os
from dotenv import load_dotenv

load_dotenv()

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
    
    # Security check for Manager PIN
    if not os.getenv("MANAGER_REGISTRATION_PIN"):
        logger.warning("SECURITY WARNING: MANAGER_REGISTRATION_PIN is not set. Using default '1234'. Set this environment variable in production!")

    logger.info("Application startup complete. Database ready.")
    yield
    # Shutdown
    logger.info("Application shutdown.")

app = FastAPI(title="Planner V2", lifespan=lifespan)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from .routers import auth, manager, employee, scheduler, health, bug_report
app.include_router(auth.router)
app.include_router(manager.router)
app.include_router(employee.router)
app.include_router(scheduler.router)
app.include_router(health.router)
app.include_router(bug_report.router)

@app.get("/")
def read_root():
    return {"message": "Planner V2 API is running"}
# Reload trigger
