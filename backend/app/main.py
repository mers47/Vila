from contextlib import asynccontextmanager
import time
import uuid

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram, make_asgi_app

from app.api.routes import (
    audit_logs, auth, campaigns, contacts, discovery, discovery_jobs, health, imports,
    leads, ops, outreach, sales, scoring, web_discovery, webhooks,
)
from app.connectors.http import HttpClient
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.startup import validate_production_settings
from app.db.session import engine
from app.services.redis_pool import close_redis_pool

configure_logging()
s = get_settings()
HTTP_REQUESTS = Counter(
    "lead_platform_http_requests_total", "HTTP requests", ["method", "route", "status"]
)
HTTP_DURATION = Histogram(
    "lead_platform_http_request_duration_seconds", "HTTP request duration", ["method", "route"]
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    validate_production_settings(s)
    yield
    await HttpClient.close_pool()
    await close_redis_pool()
    await engine.dispose()


app = FastAPI(
    title=s.app_name,
    version="2.0.0",
    docs_url="/docs" if s.environment != "production" else None,
    redoc_url=None,
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[s.frontend_origin],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Idempotency-Key"],
)


@app.middleware("http")
async def request_observability(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    started = time.perf_counter()
    log = structlog.get_logger("http")
    raw_path = request.url.path
    try:
        response = await call_next(request)
    except Exception:
        duration = time.perf_counter() - started
        HTTP_REQUESTS.labels(request.method, "__unhandled__", "500").inc()
        HTTP_DURATION.labels(request.method, "__unhandled__").observe(duration)
        log.exception("request_failed", request_id=request_id, method=request.method, path=raw_path)
        raise
    duration = time.perf_counter() - started
    route_obj = request.scope.get("route")
    route_label = getattr(route_obj, "path", "__unmatched__")
    response.headers["X-Request-ID"] = request_id
    HTTP_REQUESTS.labels(request.method, route_label, str(response.status_code)).inc()
    HTTP_DURATION.labels(request.method, route_label).observe(duration)
    log.info(
        "request_completed", request_id=request_id, method=request.method, path=raw_path, route=route_label,
        status=response.status_code, duration_ms=round(duration * 1000, 2),
    )
    return response


@app.middleware("http")
async def cookie_csrf_guard(request: Request, call_next):
    unsafe = request.method.upper() in {"POST", "PUT", "PATCH", "DELETE"}
    cookie_session = bool(request.cookies.get("access_token") or request.cookies.get("refresh_token"))
    is_api = request.url.path.startswith(s.api_v1_prefix)
    is_webhook = request.url.path.startswith(f"{s.api_v1_prefix}/webhooks/")
    if unsafe and cookie_session and is_api and not is_webhook:
        if request.headers.get("origin") != s.frontend_origin.rstrip("/"):
            return JSONResponse({"detail": "invalid request origin"}, status_code=403)
    return await call_next(request)


app.include_router(health.router)
for router in [
    auth.router, leads.router, campaigns.router, outreach.router, discovery.router,
    web_discovery.router, imports.router, scoring.router, sales.router, audit_logs.router,
    discovery_jobs.router, contacts.router, ops.router, webhooks.router,
]:
    app.include_router(router, prefix=s.api_v1_prefix)
app.mount("/metrics", make_asgi_app())