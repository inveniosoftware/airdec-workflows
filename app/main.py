import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from temporalio.client import Client

from .config import settings
from .database.session import init_engine, dispose_engine
from .dependencies import verify_jwt
from .routers import workflows

TEMPORAL_HOST = os.getenv("TEMPORAL_HOST", "localhost:7233")


@asynccontextmanager
async def lifespan(app: FastAPI):
    engine = init_engine()
    app.state.db_engine = engine
    app.state.temporal_client = await Client.connect(TEMPORAL_HOST)
    yield
    dispose_engine()


app = FastAPI(lifespan=lifespan)

if settings.DISABLE_AUTH:
    app.include_router(workflows.router)
else:
    app.include_router(
        workflows.router,
        dependencies=[Depends(verify_jwt)],
    )


@app.get("/")
async def root():
    return {"message": "This is the backend service for AIRDEC!"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)