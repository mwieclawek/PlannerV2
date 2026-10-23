from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import logging
from logging.handlers import RotatingFileHandler
import os
import time
import jwt
from dotenv import load_dotenv

load_dotenv()

from .services.log_service import TenantLogFilter
from .tenant_context import set_current_tenant_id
from .auth_utils import SECRET_KEY, ALGORITHM

os.makedirs("logs", exist_ok=True)
tenant_filter = TenantLogFilter()

file_handler = RotatingFileHandler("logs/planner.log", maxBytes=5*1024*1024, backupCount=3, encoding="utf-8")
file_handler.addFilter(tenant_filter)
file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] [%(tenant_str)s] %(name)s: %(message)s"))

stream_handler = logging.StreamHandler()
stream_handler.addFilter(tenant_filter)
stream_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] [%(tenant_str)s] %(name)s: %(message)s"))

logging.root.handlers = [file_handler, stream_handler]
logging.root.setLevel(logging.DEBUG)
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
        raise ValueError("SECURITY STOP: JWT_SECRET_KEY is not set!")
    if not os.getenv("MANAGER_REGISTRATION_PIN"):
        raise ValueError("SECURITY STOP: MANAGER_REGISTRATION_PIN is not set!")

    if not os.getenv("ENCRYPTION_KEY"):
        logger.warning(
            "ENCRYPTION_KEY is not set: Google OAuth tokens are stored UNENCRYPTED. "
            "Generate one with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )

    logger.info("Application startup complete.")
    yield
    from .database import engine
    engine.dispose()
    logger.info("Application shutdown.")


app = FastAPI(title="Planner V2", lifespan=lifespan)

# ── Rate Limiting ──────────────────────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.middleware("http")
async def log_requests_middleware(request: Request, call_next):
    start_time = time.time()
    auth_header = request.headers.get("authorization")
    if auth_header and auth_header.startswith("Bearer "):
        try:
            token = auth_header.split(" ", 1)[1]
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options={"verify_exp": False})
            tid = payload.get("tenant_id")
            if tid is not None:
                set_current_tenant_id(int(tid))
        except Exception:
            pass

    try:
        response = await call_next(request)
        duration_ms = int((time.time() - start_time) * 1000)
        path = request.url.path
        if not path.startswith("/health") and path != "/":
            status_code = response.status_code
            msg = f"{request.method} {path} -> {status_code} ({duration_ms}ms)"
            if status_code >= 500:
                logger.error(msg)
            elif status_code >= 400:
                logger.warning(msg)
            elif request.method in ("POST", "PUT", "PATCH", "DELETE"):
                logger.info(msg)
            elif duration_ms >= 1000:
                logger.warning(f"SLOW {msg}")
            else:
                logger.debug(msg)
        return response
    except Exception as exc:
        duration_ms = int((time.time() - start_time) * 1000)
        logger.error(f"{request.method} {request.url.path} -> EXCEPTION: {exc} ({duration_ms}ms)", exc_info=True)
        raise exc


_raw_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5000,http://127.0.0.1:5000,http://localhost:8080,http://127.0.0.1:8080")
allowed_origins = [o.strip() for o in _raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from .routers import auth, manager, employee, scheduler, health, bug_report, notifications, kitchen, pos, admin, sysadmin
app.include_router(auth.router)
app.include_router(manager.router)
app.include_router(employee.router)
app.include_router(scheduler.router)
app.include_router(health.router)
app.include_router(bug_report.router)
app.include_router(notifications.router)
app.include_router(kitchen.router)
app.include_router(pos.router)
app.include_router(admin.router)
app.include_router(admin.router, prefix="/api")
app.include_router(sysadmin.router)

@app.get("/")
def read_root():
    return {"message": "Planner V2 API is running"}
