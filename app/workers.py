import argparse
import asyncio

from pydantic_ai.durable_exec.temporal import PydanticAIPlugin
from temporalio.client import Client
from temporalio.worker import Worker

from app.activities import REGISTERED_ACTIVITIES
from app.config import get_settings
from app.database.session import init_engine
from app.workflows.queues import DEFAULT_TASK_QUEUE
from app.workflows.registry import get_registered_task_queues, get_specs_for_task_queue
from app.workflows.specs import WorkflowSpec


async def _run_worker(
    client: Client, task_queue: str, specs: list[WorkflowSpec]
) -> None:
    worker = Worker(
        client,
        task_queue=task_queue,
        workflows=[spec.workflow_cls for spec in specs],
        activities=REGISTERED_ACTIVITIES,
    )
    await worker.run()


async def main(task_queue: str | None = None):
    """Start the Temporal worker."""
    init_engine()
    settings = get_settings()
    task_queue = task_queue or DEFAULT_TASK_QUEUE
    workflow_specs = get_specs_for_task_queue(task_queue)
    if not workflow_specs:
        registered = ", ".join(get_registered_task_queues()) or "(none)"
        raise ValueError(
            f"No workflows registered for task queue {task_queue!r}. "
            f"Registered task queues: {registered}"
        )

    client = await Client.connect(
        settings.temporal_host,
        plugins=[PydanticAIPlugin()],
    )

    await _run_worker(client, task_queue, workflow_specs)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Start a Temporal worker.")
    parser.add_argument(
        "--task-queue",
        help="Task queue this worker process should poll.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    asyncio.run(main(args.task_queue))
