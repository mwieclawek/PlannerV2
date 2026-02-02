from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup - Alembic migrations run before uvicorn via entrypoint.sh
    logger.info("Application startup complete. Database migrations handled by Alembic.")
    yield
    # Shutdown
    logger.info("Application shutdown.")

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
