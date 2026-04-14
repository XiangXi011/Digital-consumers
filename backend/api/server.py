"""
FastAPI HTTP API entrypoint for the web frontend.

Run with:
    python -m uvicorn api_server:app --reload --port 8000
"""

import logging
import os
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from backend.api.routers import dashboard, image_generation, personas, projects, reports, settings, upload
from backend.auth.routes import router as auth_router
from backend.infra.logging_config import configure_structlog, generate_request_id, request_id_var
from backend.infra.otel_config import configure_otel
from backend.infra.redis_infra import create_store
from backend.paths import OUTPUTS_DIR

# Configure structured logging
configure_structlog()
logger = logging.getLogger(__name__)

OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="数字消费者洞察平台 API",
    description="为市场部 Agent Teams 前端提供数据接口",
    version="0.1.0",
)


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Inject a unique request_id into every request for log correlation."""

    async def dispatch(self, request: Request, call_next):
        rid = request.headers.get("X-Request-ID") or generate_request_id()
        token = request_id_var.set(rid)
        start = time.time()
        try:
            response = await call_next(request)
            duration_ms = round((time.time() - start) * 1000, 1)
            logger.info(
                "%s %s %s %.1fms",
                request.method,
                request.url.path,
                response.status_code,
                duration_ms,
            )
            response.headers["X-Request-ID"] = rid
            return response
        except Exception:
            duration_ms = round((time.time() - start) * 1000, 1)
            logger.exception(
                "%s %s FAILED %.1fms",
                request.method,
                request.url.path,
                duration_ms,
            )
            raise
        finally:
            request_id_var.reset(token)


app.add_middleware(RequestIdMiddleware)

_allowed_origins = os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _allowed_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)

app.include_router(auth_router)
app.include_router(personas.router, prefix="/api", tags=["画像库"])
app.include_router(reports.router, prefix="/api", tags=["报告中心"])
app.include_router(projects.router, prefix="/api", tags=["项目管理"])
app.include_router(dashboard.router, prefix="/api", tags=["仪表盘"])
app.include_router(settings.router, prefix="/api", tags=["系统设置"])
app.include_router(upload.router, prefix="/api", tags=["文件上传"])
app.include_router(image_generation.router, prefix="/api", tags=["生图"])

app.mount("/outputs", StaticFiles(directory=str(OUTPUTS_DIR)), name="outputs")


@app.on_event("startup")
async def startup_infrastructure():
    """Initialize shared infrastructure on app startup."""
    redis_url = os.getenv("REDIS_URL", "")
    app.state.store = create_store(redis_url)
    store_type = type(app.state.store).__name__
    logger.info("KeyValueStore initialized: %s", store_type)

    # Phase 3: OpenTelemetry observability
    configure_otel(service_name="market-agent-backend")


@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "数字消费者洞察平台"}


@app.get("/metrics")
def prometheus_metrics():
    """Prometheus-compatible metrics endpoint."""
    try:
        from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
        from fastapi.responses import Response

        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
    except ImportError:
        return {"error": "prometheus_client not installed"}
