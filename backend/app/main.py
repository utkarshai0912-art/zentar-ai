import asyncio
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


class StartupHealth:
    def __init__(self):
        self.started = False
        self.services = {
            "database": False,
            "skills": False,
            "agents": False,
            "browser": False,
            "marketplace": False,
            "scheduler": False,
        }
        self.errors: dict[str, str] = {}

    def mark(self, service: str, ok: bool, error: str = ""):
        self.services[service] = ok
        if error:
            self.errors[service] = error

    @property
    def all_ok(self) -> bool:
        return all(self.services.values())

    @property
    def summary(self) -> dict:
        return {
            "started": self.started,
            "services": dict(self.services),
            "errors": dict(self.errors) if self.errors else None,
        }


startup_health = StartupHealth()


app = FastAPI(
    title="Zentar Intelligence API",
    version="1.0.0",
    description="AI-powered Android assistant backend with multi-provider AI, "
                "MCP protocol, plugin system, and automation engine.",
    docs_url="/docs",
    redoc_url="/redoc",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def timing_middleware(request: Request, call_next):
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


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
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


async def _init_background():
    startup_health.started = True
    logger.info("Starting background initialization...")

    try:
        await init_db()
        startup_health.mark("database", True)
        logger.info("Database initialized")
    except Exception as e:
        startup_health.mark("database", False, str(e))
        logger.warning("Database initialization skipped: %s", e)

    try:
        register_builtin_skills()
        startup_health.mark("skills", True)
        logger.info("Built-in skills registered")
    except Exception as e:
        startup_health.mark("skills", False, str(e))
        logger.warning("Skill registration skipped: %s", e)

    try:
        register_agent_tools()
        startup_health.mark("agents", True)
        logger.info("Agent tools registered")
    except Exception as e:
        startup_health.mark("agents", False, str(e))
        logger.warning("Agent tools registration skipped: %s", e)

    try:
        register_managers()
        register_workers()
        logger.info("Manager and worker agents registered")
    except Exception as e:
        logger.warning("Agent registration skipped: %s", e)

    try:
        await browser_service.start(headless=True)
        startup_health.mark("browser", True)
        logger.info("Browser service started")
    except Exception as e:
        startup_health.mark("browser", False, str(e))
        logger.warning("Browser service start skipped: %s", e)

    try:
        marketplace_reader.load_all()
        stats = marketplace_reader.get_stats()
        startup_health.mark("marketplace", True)
        logger.info(
            "Marketplace loaded: %d agents from %d plugins",
            stats["total_agents"],
            stats["total_plugins"],
        )
    except Exception as e:
        startup_health.mark("marketplace", False, str(e))
        logger.warning("Marketplace load skipped: %s", e)

    try:
        register_default_tasks()
        await scheduler.start()
        startup_health.mark("scheduler", True)
        logger.info("Scheduler started")
    except Exception as e:
        startup_health.mark("scheduler", False, str(e))
        logger.warning("Scheduler start skipped: %s", e)

    ok_count = sum(1 for v in startup_health.services.values() if v)
    total = len(startup_health.services)
    logger.info("Background initialization complete (%d/%d services ok)", ok_count, total)


@app.on_event("startup")
async def startup():
    logger.info("Starting Zentar Intelligence API...")
    asyncio.create_task(_init_background())
    logger.info("Zentar Intelligence API accepting requests (background init in progress)")


@app.on_event("shutdown")
async def shutdown():
    logger.info("Shutting down Zentar Intelligence API...")
    await scheduler.stop()
    await close_db()
    await close_redis()
    try:
        await browser_service.stop()
        logger.info("Browser service stopped")
    except Exception as e:
        logger.warning("Browser service stop skipped: %s", e)
    logger.info("Zentar Intelligence API shut down")


app.include_router(api_v1_router)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "zentar-intelligence",
        "version": "1.0.0",
        "startup": startup_health.summary,
    }


@app.get("/")
async def root():
    return {
        "name": "Zentar Intelligence API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }
