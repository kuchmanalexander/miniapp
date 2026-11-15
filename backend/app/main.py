import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import check_settings, settings
from app.errors import ApiError
from app.logging_setup import request_id_var, setup_logging
from app.notify import notify_admins
from app.ratelimit import client_ip
from app.routers import auth as auth_router
from app.routers import devpage as devpage_router
from app.routers import me as me_router

API_PREFIX = "/api/v1"

setup_logging(settings.log_level)
logger = logging.getLogger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    check_settings(settings)
    logger.info("Сервер запущен, окружение: %s", settings.app_env)
    yield


app = FastAPI(title="HSE English Prep API", version="0.2.0", lifespan=lifespan)


@app.middleware("http")
async def request_context(request: Request, call_next):
    """Присваивает запросу номер и пишет строку в журнал."""
    request_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
    request.state.request_id = request_id
    request_id_var.set(request_id)

    started = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - started) * 1000

    if request.url.path != "/health":
        logger.info(
            "%s %s -> %s (%.0f мс, ip=%s)",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
            client_ip(request),
        )
    response.headers["X-Request-ID"] = request_id
    return response


# CORS добавляем последним, чтобы он оборачивал все остальное
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(ApiError)
async def api_error_handler(request: Request, exc: ApiError):
    """Все ошибки API отдаём в едином формате {code, message}."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.code, "message": exc.message},
        headers=exc.headers,
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    """Ошибки в данных запроса тоже отдаём в едином формате."""
    return JSONResponse(
        status_code=422,
        content={"code": "validation_error", "message": "Некорректные данные запроса"},
    )


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception):
    """Любая непредвиденная ошибка: пишем в журнал, сообщаем админам, клиенту отдаём 500."""
    request_id = getattr(request.state, "request_id", "-")
    logger.error(
        "Необработанная ошибка [%s] %s %s",
        request_id,
        request.method,
        request.url.path,
        exc_info=exc,
    )
    notify_admins(
        f"⚠️ Ошибка сервера API\n"
        f"{request.method} {request.url.path}\n"
        f"request_id: {request_id}\n"
        f"{type(exc).__name__}: {exc}",
        key=f"{type(exc).__name__}|{request.url.path}",
    )
    return JSONResponse(
        status_code=500,
        content={
            "code": "internal_error",
            "message": "Внутренняя ошибка сервера",
            "request_id": request_id,
        },
    )


@app.get("/health")
def health():
    """Проверка, что сервер работает."""
    return {"status": "ok", "env": settings.app_env}


app.include_router(auth_router.router, prefix=API_PREFIX)
app.include_router(me_router.router, prefix=API_PREFIX)
app.include_router(devpage_router.router)