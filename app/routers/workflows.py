from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlmodel import Session, select
from temporalio.client import Client
import asyncio
from app.database.models import Workflow, WorkflowStatus
from app.database.session import get_session
from app.workflows.extract_metadata_workflow import ExtractMetadata
from sqlalchemy.exc import SQLAlchemyError
from pyrate_limiter import Duration, Limiter, Rate
from fastapi_limiter.depends import RateLimiter


router = APIRouter(
    prefix="/workflows",
    tags=["workflows"],
    responses={404: {"description": "Not found"}},
)

STREAM_DELAY = 1


class CreateWorkflowRequest(BaseModel):
    url: str


def _get_temporal_client(request: Request) -> Client:
    return request.app.state.temporal_client


@router.get(
    "/",
    dependencies=[
        Depends(RateLimiter(limiter=Limiter(Rate(10, Duration.SECOND * 30))))
    ],
)
async def read_workflows(session: Session = Depends(get_session)):
    workflows = session.exec(select(Workflow)).all()
    return [workflow.to_dict() for workflow in workflows]


@router.post(
    "/",
    dependencies=[Depends(RateLimiter(limiter=Limiter(Rate(1, Duration.SECOND * 10))))],
)
async def create_workflow(
    body: CreateWorkflowRequest,
    request: Request,
    session: Session = Depends(get_session),
):
    workflow = Workflow(status=WorkflowStatus.PROCESSING, url=body.url, user_id="123")
    try:
        session.add(workflow)
        session.commit()
        workflow_id = workflow.public_id
    except SQLAlchemyError as e:
        print("Error(create_workflow)", e)
        raise HTTPException(status_code=500, detail="Could not create workflow")

    try:
        client = _get_temporal_client(request)
        await client.start_workflow(
            ExtractMetadata.run,
            args=[body.url],
            id=f"extract-metadata-{workflow_id}",
            task_queue="extract-pdf-metadata-task-queue",
        )
        workflow.status = WorkflowStatus.SUCCESS
        session.commit()
    except Exception as e:
        print("Error(start_temporal_workflow)", e)
        try:
            workflow.status = WorkflowStatus.ERROR
            session.commit()
        except SQLAlchemyError:
            pass
        raise HTTPException(
            status_code=500, detail="Could not start extraction workflow"
        )

    return {"public_id": workflow_id, "status": "PROCESSING"}


@router.get(
    "/{workflow_id}",
    dependencies=[
        Depends(RateLimiter(limiter=Limiter(Rate(10, Duration.SECOND * 30))))
    ],
)
async def read_workflow(
    workflow_id: str,
    session: Session = Depends(get_session),
):
    try:
        workflow = session.exec(
            select(Workflow).where(Workflow.public_id == workflow_id)
        ).one()
        return workflow.to_dict()
    except SQLAlchemyError as e:
        print("Error(read_workflow)", e)
        raise HTTPException(status_code=404, detail="Workflow not found")


async def workflow_event(request: Request, workflow_id: str):
    while True:
        if await request.is_disconnected():
            break

        with Session(request.app.state.db_engine) as session:
            try:
                workflow = session.exec(
                    select(Workflow).where(Workflow.public_id == workflow_id)
                ).one()
                if workflow.status.name == "ERROR" or workflow.status.name == "SUCCESS":
                    yield workflow.status.name
                    break

                yield workflow.status.name
            except SQLAlchemyError as e:
                print("Error(stream_workflow)", e)
                raise HTTPException(status_code=500)

        await asyncio.sleep(STREAM_DELAY)


@router.get("/{workflow_id}/stream")
async def stream_workflow(request: Request, workflow_id: str):
    return StreamingResponse(
        workflow_event(request, workflow_id), media_type="text/event-stream"
    )
