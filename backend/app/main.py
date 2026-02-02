from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import init_db
from contextlib import asynccontextmanager
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Retry DB connection
    max_retries = 5
    for i in range(max_retries):
        try:
            init_db()
            logger.info("Database initialized successfully.")
            break
        except Exception as e:
            logger.warning(f"Database connection failed (attempt {i+1}/{max_retries}): {e}")
            if i == max_retries - 1:
                logger.error("Could not connect to database after retries. Exiting.")
                # We could raise here to crash container if critical
            time.sleep(5)
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
