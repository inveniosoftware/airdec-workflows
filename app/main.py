import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from temporalio.client import Client

from .database.session import init_engine, dispose_engine
from .dependencies import get_token_header
from .routers import workflows

TEMPORAL_HOST = os.getenv("TEMPORAL_HOST", "localhost:7233")


@asynccontextmanager
async def lifespan(app: FastAPI):
    engine = init_engine()
    app.state.db_engine = engine
    app.state.temporal_client = await Client.connect(TEMPORAL_HOST)
    yield
    dispose_engine()


app = FastAPI(dependencies=[Depends(get_token_header)], lifespan=lifespan)


app.include_router(
    workflows.router,
    dependencies=[Depends(get_token_header)],
)


@app.get("/")
async def root():
    return {"message": "This is the backend service for AIRDEC!"}
