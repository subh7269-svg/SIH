import uuid
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError, HTTPException

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.core.errors import TraceXException, tracex_exception_handler, generic_http_exception_handler
from backend.app.db.base import Base
from backend.app.db.session import engine
import backend.app.models  # Ensure all SQLAlchemy models are registered

# Ensure Starlette MultiPartParser supports multi-gigabyte forensic file uploads without 400 Bad Request
import starlette.formparsers
try:
    if hasattr(starlette.formparsers.MultiPartParser, "__init__") and hasattr(starlette.formparsers.MultiPartParser.__init__, "__kwdefaults__"):
        kw = starlette.formparsers.MultiPartParser.__init__.__kwdefaults__
        if kw:
            kw["max_part_size"] = 1024 * 1024 * 1024  # 1 GB
            kw["max_files"] = 5000
            kw["max_fields"] = 5000
except Exception as e:
    logger.warning(f"Could not adjust MultiPartParser kwdefaults: {e}")

# Import routers
from backend.app.api.v1.health import router as health_router
from backend.app.api.v1.auth import router as auth_router
from backend.app.api.v1.datasets import router as datasets_router
from backend.app.api.v1.entities import router as entities_router
from backend.app.api.v1.graph import router as graph_router
from backend.app.api.v1.models import router as models_router
from backend.app.api.v1.clusters import router as clusters_router
from backend.app.api.v1.alerts import router as alerts_router
from backend.app.api.v1.investigations import router as investigations_router
from backend.app.api.v1.reports import router as reports_router
from backend.app.api.v1.demo import router as demo_router
from backend.app.api.v1.jobs import router as jobs_router
from backend.app.api.v1.correlation import router as correlation_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Create tables if not exist
    Base.metadata.create_all(bind=engine)
    logger.info("TraceX Backend Initialized. Database tables verified.")
    yield
    logger.info("TraceX Backend Shutting Down.")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=(
        "TraceX: AI-Powered Bitcoin Transaction Investigation & Risk Intelligence Platform. "
        "Offline-compatible system correlating network P2P metadata with blockchain transactions, "
        "extracting behavioral features, training Isolation Forest anomaly detectors, and generating explainable alerts."
    ),
    openapi_url="/api/v1/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request ID & Logging Middleware
@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    req_id = request.headers.get("X-Request-ID", str(uuid.uuid4())[:8])
    request.state.request_id = req_id
    start_time = time.time()

    response = await call_next(request)
    process_time = round((time.time() - start_time) * 1000, 2)

    response.headers["X-Request-ID"] = req_id
    response.headers["X-Process-Time-MS"] = str(process_time)
    return response

# Central Exception Handlers
app.add_exception_handler(TraceXException, tracex_exception_handler)
app.add_exception_handler(HTTPException, generic_http_exception_handler)

# Include Routers under /api/v1
api_v1 = settings.API_V1_STR
app.include_router(health_router, prefix=api_v1)
app.include_router(auth_router, prefix=api_v1)
app.include_router(datasets_router, prefix=api_v1)
app.include_router(entities_router, prefix=api_v1)
app.include_router(graph_router, prefix=api_v1)
app.include_router(models_router, prefix=api_v1)
app.include_router(clusters_router, prefix=api_v1)
app.include_router(alerts_router, prefix=api_v1)
app.include_router(investigations_router, prefix=api_v1)
app.include_router(reports_router, prefix=api_v1)
app.include_router(demo_router, prefix=api_v1)
app.include_router(jobs_router, prefix=api_v1)

# Correlation Engine Routers (mounted on /api and /api/v1)
app.include_router(correlation_router, prefix="/api")
app.include_router(correlation_router, prefix=api_v1)

@app.get("/")
def root():
    return {
        "platform": "TraceX Bitcoin Investigation Platform",
        "version": settings.VERSION,
        "docs": "/docs",
        "api_v1": api_v1,
        "mode": "offline-ready",
        "compliance": "Investigative analytics platform. Anomaly detection produces investigative leads, not guilt proof."
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
