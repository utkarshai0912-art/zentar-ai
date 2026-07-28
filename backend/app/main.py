"""
Zentar Intelligence — Main Application Entry

FastAPI application initialization with middleware, routes, health checks,
and lifecycle management.
"""

import logging
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1 import api_v1_router
from app.core.config import get_settings
from app.core.database import close_db, init_db
from app.core.redis_client import close_redis
from app.skills.manager import register_builtin_skills
from app.workers.scheduler import register_default_tasks, scheduler
from app.agents.tools.agent_tools import register_agent_tools
from app.agents.manager_agents import register_managers
from app.agents.worker_agents import register_workers
from app.agents.marketplace import marketplace_reader
from app.services.browser_service import browser_service

logger = logging.getLogger("zentar.main")

settings = get_settings()

# ── Application Setup ─────────────────────

app = FastAPI(
    title="Zentar Intelligence API",
    version="1.0.0",
    description="AI-powered Android assistant backend with multi-provider AI, "
                "MCP protocol, plugin system, and automation engine.",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── Middleware ─────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def timing_middleware(request: Request, call_next):
    """Log request timing, warn on slow requests (>5s)."""
    start = time.time()
    response = await call_next(request)
    elapsed = time.time() - start
    if elapsed > 5:
        logger.warning(
            "Slow request: %s %s took %.2fs",
            request.method,
            request.url.path,
            elapsed,
        )
    response.headers["X-Process-Time-MS"] = str(round(elapsed * 1000, 2))
    return response


# ── Exception Handler ─────────────────────


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch unhandled exceptions and return a clean error response."""
    logger.error(
        "Unhandled exception: %s %s: %s",
        request.method,
        request.url.path,
        exc,
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "type": type(exc).__name__,
        },
    )


# ── Lifecycle Events ──────────────────────


@app.on_event("startup")
async def startup():
    """Initialize services on startup."""
    logger.info("Starting Zentar Intelligence API...")

    # Initialize database
    try:
        await init_db()
        logger.info("Database initialized")
    except Exception as e:
        logger.warning("Database initialization skipped: %s", e)

    # Register built-in skills
    try:
        register_builtin_skills()
        logger.info("Built-in skills registered")
    except Exception as e:
        logger.warning("Skill registration skipped: %s", e)

    # Register agent tools
    try:
        register_agent_tools()
        logger.info("Agent tools registered")
    except Exception as e:
        logger.warning("Agent tools registration skipped: %s", e)

    # Register manager and worker agents
    try:
        register_managers()
        register_workers()
        logger.info("Manager and worker agents registered")
    except Exception as e:
        logger.warning("Agent registration skipped: %s", e)

    # Start browser service
    try:
        await browser_service.start(headless=True)
        logger.info("Browser service started")
    except Exception as e:
        logger.warning("Browser service start skipped: %s", e)

    # Load marketplace agents
    try:
        marketplace_reader.load_all()
        stats = marketplace_reader.get_stats()
        logger.info(
            "Marketplace loaded: %d agents from %d plugins",
            stats["total_agents"],
            stats["total_plugins"],
        )
    except Exception as e:
        logger.warning("Marketplace load skipped: %s", e)

    # Register and start scheduler tasks
    try:
        register_default_tasks()
        await scheduler.start()
        logger.info("Scheduler started")
    except Exception as e:
        logger.warning("Scheduler start skipped: %s", e)

    logger.info("Zentar Intelligence API started")


@app.on_event("shutdown")
async def shutdown():
    """Clean up on shutdown."""
    logger.info("Shutting down Zentar Intelligence API...")

    # Stop scheduler
    await scheduler.stop()

    # Close database connections
    await close_db()

    # Close Redis
    await close_redis()

    # Stop browser service
    try:
        await browser_service.stop()
        logger.info("Browser service stopped")
    except Exception as e:
        logger.warning("Browser service stop skipped: %s", e)

    logger.info("Zentar Intelligence API shut down")


# ── Routes ─────────────────────────────────

app.include_router(api_v1_router)


# ── Health Check ──────────────────────────


@app.get("/health")
async def health():
    """Basic health check endpoint."""
    return {
        "status": "ok",
        "version": "1.0.0",
        "service": "zentar-intelligence",
    }


@app.get("/")
async def root():
    """Root info endpoint."""
    return {
        "name": "Zentar Intelligence API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }
