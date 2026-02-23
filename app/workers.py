import os
import asyncio

from temporalio.client import Client
from temporalio.worker import Worker

from pydantic_ai.durable_exec.temporal import PydanticAIPlugin

from app.workflows.extract_metadata_workflow import ExtractMetadata
from app.activities import extract_pdf_content

TEMPORAL_HOST = os.getenv("TEMPORAL_HOST", "localhost:7233")


async def main():
    client = await Client.connect(
        TEMPORAL_HOST,
        plugins=[PydanticAIPlugin()],
    )

    worker = Worker(
        client,
        task_queue="extract-pdf-metadata-task-queue",
        workflows=[
            ExtractMetadata,
        ],
        activities=[
            extract_pdf_content.create,
        ],
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
