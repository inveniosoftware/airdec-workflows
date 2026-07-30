# SPDX-FileCopyrightText: 2026 CERN.
# SPDX-License-Identifier: MIT

"""FastAPI application entry point with multi-tenant auth."""

import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.exception_handlers import (
    http_exception_handler,
    request_validation_exception_handler,
)
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from .config import get_settings
from .database.session import dispose_engine, init_engine
from .dependencies import get_current_user
from .routers import workflow_feedback, workflows
from .temporal import dispose_temporal_client, init_temporal_client
from .tenants import TenantRegistry

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and tear down application resources."""
    settings = get_settings()
    engine = init_engine()
    app.state.db_engine = engine
    await init_temporal_client()

    # Load tenant registry
    if not settings.auth_disabled:
        app.state.tenant_registry = TenantRegistry.from_file(
            settings.tenants_config_path,
        )
    else:
        app.state.tenant_registry = TenantRegistry()

    yield
    dispose_temporal_client()
    dispose_engine()


app = FastAPI(lifespan=lifespan)

# Apply CORS middleware using settings
_settings = get_settings()
if _settings.allowed_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_settings.allowed_origins,
        allow_methods=["GET"],
        allow_headers=["*"],
    )


app.include_router(workflows.router)
app.include_router(workflow_feedback.router)


@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request, exc):
    """Custom error handling for logging HTTP errors."""
    logger.warning(
        "HTTP %s on %s %s: %s",
        exc.status_code,
        request.method,
        request.url.path,
        exc.detail,
    )
    return await http_exception_handler(request, exc)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Custom error handling for logging the Pydantic validation errors."""
    logger.warning(
        "Validation error on %s %s: %s",
        request.method,
        request.url.path,
        exc.errors(),
    )
    return await request_validation_exception_handler(request, exc)


@app.get("/healthz")
async def healthz():
    """Health check endpoint for Kubernetes probes."""
    return {"status": "ok"}


@app.get("/")
async def root(auth=Depends(get_current_user)):
    """Root endpoint."""
    return {"message": "This is the backend service for Orcha!"}
