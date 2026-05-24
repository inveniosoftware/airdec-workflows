# SPDX-FileCopyrightText: 2026 CERN.
# SPDX-License-Identifier: MIT

from datetime import timedelta

from pydantic import Field, HttpUrl
from pydantic_ai.durable_exec.temporal import (
    PydanticAIWorkflow,
)
from temporalio import workflow

from app.activities.extract_metadata import (
    ExtractMetadataRequest,
    extract_metadata_with_llm,
)
from app.activities.extract_pdf_content import (
    ExtractPdfContentRequest,
    extract_pdf_text,
)
from app.activities.store_workflow_result import (
    WorkflowResultInput,
    store_workflow_result,
)
from app.database.models import WorkflowStatus
from app.schemas.metadata_suggestions import MetadataSuggestions
from app.workflows.specs import (
    WorkflowContext,
    WorkflowParams,
)


class ExtractMetadataParams(WorkflowParams):
    """User-provided params for the extract_metadata workflow."""

    url: HttpUrl
    extractor: str = "pdfplumber"
    pages: list[int] | None = Field(default_factory=lambda: [1, 2])


@workflow.defn
class ExtractMetadata(PydanticAIWorkflow):
    """Workflow that extracts content from a PDF and uses an LLM to extract metadata."""

    @workflow.run
    async def run(
        self,
        context: WorkflowContext,
        params: ExtractMetadataParams,
    ) -> MetadataSuggestions:
        """Execute the extraction + suggestions workflow."""
        try:
            # Activity 1: Extract PDF text
            content = await workflow.execute_activity(
                extract_pdf_text,
                ExtractPdfContentRequest(
                    url=str(params.url),
                    extractor=params.extractor,
                    pages=params.pages,
                ),
                start_to_close_timeout=timedelta(minutes=5),
            )

            # Activity 2: Generate metadata suggestions using LLM
            result = await workflow.execute_activity(
                extract_metadata_with_llm,
                ExtractMetadataRequest(text=content.text),
                start_to_close_timeout=timedelta(minutes=5),
            )
        except Exception:
            await workflow.execute_activity(
                store_workflow_result,
                WorkflowResultInput(
                    workflow_id=context.workflow_id,
                    tenant_id=context.tenant_id,
                    status=WorkflowStatus.ERROR,
                    result=None,
                ),
                start_to_close_timeout=timedelta(minutes=1),
            )
            raise

        await workflow.execute_activity(
            store_workflow_result,
            WorkflowResultInput(
                workflow_id=context.workflow_id,
                tenant_id=context.tenant_id,
                status=WorkflowStatus.SUCCESS,
                result=result.model_dump(),
            ),
            start_to_close_timeout=timedelta(minutes=1),
        )

        return result
