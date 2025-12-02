from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from redis import asyncio as aioredis

from api.v1 import activities, analytics, auth, contacts, deals, organizations, tasks
from core import redis
from core.cache import RedisCache
from core.config import logger, settings
from core.database import engine
from core.exceptions import CRMException
from core.redis import CacheDep


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:  # type: ignore[misc]
    """Lifespan context manager для управления ресурсами."""
    # Startup: инициализация ресурсов
    redis_client = aioredis.from_url(
        f"redis://{settings.redis_host}:{settings.redis_port}",
        encoding="utf-8",
        decode_responses=True,
    )

    # Проверка подключения к Redis
    try:
        await redis_client.ping()
        logger.info("✓ Redis connection established")
    except Exception as e:
        logger.error(f"✗ Redis connection failed: {e}")
        raise

    # Инициализация cache
    redis.cache = RedisCache(redis_client)

    # Проверка подключения к БД
    try:
        async with engine.begin() as conn:
            await conn.run_sync(lambda _: None)
        logger.info("✓ Database connection established")
    except Exception as e:
        logger.error(f"✗ Database connection failed: {e}")
        raise

    yield

    # Shutdown: закрытие ресурсов
    await redis_client.close()
    await engine.dispose()
    logger.info("✓ Resources closed successfully")


app = FastAPI(
    title=settings.project_name,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)


# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=settings.cors_methods_list,
    allow_headers=settings.cors_headers_list,
)


# Exception handlers
@app.exception_handler(CRMException)
async def crm_exception_handler(request: Request, exc: CRMException) -> JSONResponse:
    """Handle custom CRM exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle Pydantic validation errors."""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "detail": "Validation error",
            "errors": exc.errors(),
        },
    )


# Include routers
app.include_router(auth.router, prefix="/api/v1")
app.include_router(organizations.router, prefix="/api/v1")
app.include_router(contacts.router, prefix="/api/v1")
app.include_router(deals.router, prefix="/api/v1")
app.include_router(tasks.router, prefix="/api/v1")
app.include_router(activities.router, prefix="/api/v1")
app.include_router(analytics.router, prefix="/api/v1")


@app.get("/health")
async def health_check(cache: CacheDep) -> dict[str, str]:
    """Health check endpoint."""
    # Проверка cache
    try:
        await cache.set("health_check", "ok", expire=10)
        cache_status = "ok"
    except Exception:
        cache_status = "error"

    return {
        "status": "ok",
        "service": settings.project_name,
        "cache": cache_status,
    }


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {
        "message": "Mini CRM API",
        "docs": "/docs",
        "health": "/health",
    }
