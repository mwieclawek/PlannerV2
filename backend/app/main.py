from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import logging
import os
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Rate Limiter ───────────────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address)

@asynccontextmanager
async def lifespan(app: FastAPI):
    from .database import init_db, DATABASE_URL

    logger.info(f"Initializing database (URL starts with: {DATABASE_URL[:10]}...)...")
    init_db()

    # Security startup checks
    if not os.getenv("JWT_SECRET_KEY"):
        logger.warning(
            "SECURITY WARNING: JWT_SECRET_KEY is not set! "
            "Using an insecure development default. Set this in production!"
        )
    if not os.getenv("MANAGER_REGISTRATION_PIN"):
        logger.warning(
            "SECURITY WARNING: MANAGER_REGISTRATION_PIN is not set. Using default '1234'."
        )

    logger.info("Application startup complete.")
    yield
    logger.info("Application shutdown.")


app = FastAPI(title="Planner V2", lifespan=lifespan)

# ── Rate Limiting ──────────────────────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── CORS ───────────────────────────────────────────────────────────────────────
_raw_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5000,http://127.0.0.1:5000")
allowed_origins = [o.strip() for o in _raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from .routers import auth, manager, employee, scheduler, health, bug_report, notifications
app.include_router(auth.router)
app.include_router(manager.router)
app.include_router(employee.router)
app.include_router(scheduler.router)
app.include_router(health.router)
app.include_router(bug_report.router)
app.include_router(notifications.router)

@app.get("/")
def read_root():
    return {"message": "Planner V2 API is running"}
