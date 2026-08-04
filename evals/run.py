# SPDX-FileCopyrightText: 2026 CERN.
# SPDX-License-Identifier: MIT

"""Langfuse experiments runner using the SDK Experiments API."""

import argparse
import asyncio
import os
from io import BytesIO
from pathlib import Path

import pdfplumber
from dataset import (
    get_or_create_langfuse_dataset,
    load_local_dataset,
)
from evaluators import (
    average_score_evaluator,
    build_comparison_payload,
    item_summary_evaluator,
)
from extractors import get_extractor
from langfuse import get_client
from models import MetadataResult, create_model
from prompts import sync_extraction_prompt
from pydantic_ai import Agent

DATASET_ROOT = Path("full-dataset")
DATASET_NAME = "results-with-all-tools"
EXPERIMENT_NAME = "results-with-all-tools"


def extract_text(pdf_path: Path, extractor_name: str, pages: list[int] | None = None):
    """Read a PDF file and extract text with the configured extractor.

    If requested pages are out of range, filters to available pages only.
    """
    extractor = get_extractor(extractor_name)
    pdf_bytes = pdf_path.read_bytes()

    # If pages are specified, filter them
    if pages:
        with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
            page_count = len(pdf.pages)
            # Filter to pages that actually exist (1-based indexing)
            valid_pages = [p for p in pages if 0 < p <= page_count]
            if len(valid_pages) < len(pages):
                # If some pages are invalid, use only the valid ones
                return extractor.extract(pdf_bytes, pages=valid_pages)["full_text"]
    return extractor.extract(pdf_bytes, pages=pages)["full_text"]


def save_extracted_text(text: str, record_id: str, dataset_root: Path) -> None:
    """Save extracted text to a file in the extracted_text directory for inspection."""
    extracted_dir = dataset_root / "extracted_text"
    extracted_dir.mkdir(parents=True, exist_ok=True)

    output_path = extracted_dir / f"{record_id}.txt"
    output_path.write_text(text, encoding="utf-8")


async def _run_agent(agent: Agent, document_text: str) -> MetadataResult:
    """Run the extraction agent on document text."""
    max_retries = 5
    for attempt in range(max_retries):
        try:
            result = await agent.run(document_text)
            return result.output
        except Exception as exc:
            error_str = str(exc)
            is_retryable = (
                "429" in error_str
                or "500" in error_str
                or "Connection error" in error_str
            )
            if is_retryable and attempt < max_retries - 1:
                wait_time = 2**attempt
                print(
                    f"  Retry attempt {attempt + 1}/{max_retries - 1} "
                    f"after {wait_time}s..."
                )
                await asyncio.sleep(wait_time)
            else:
                raise


async def extraction_task(dataset_item, agent: Agent, extractor: str = "pdfplumber"):
    """Extract text, run the agent, and build evaluator comparison data."""
    input_data = dataset_item.get("input")
    pdf_path = Path(input_data.get("pdf_path"))
    expected = dataset_item.get("expected_output")

    # Extract text from pdf
    text = extract_text(pdf_path, extractor, [1, 2])

    # Run model
    output = await _run_agent(agent, text)
    output_dict = output.model_dump(mode="json")
    output_dict["comparison"] = build_comparison_payload(output_dict, expected)

    return {
        "pdf_filename": pdf_path.name,
        "comparison": output_dict["comparison"],
    }


async def run(
    extractor: str = "pdfplumber",
    prompt_name: str = "medium",
    run_name: str | None = None,
):
    """Run extraction and evaluation experiment."""
    items = load_local_dataset(DATASET_ROOT, DATASET_NAME)

    client = get_client()
    prompt_ref = sync_extraction_prompt(client, prompt_name)

    dataset_items = get_or_create_langfuse_dataset(
        client,
        DATASET_NAME,
        items,
    )

    agent = Agent(
        model=create_model(),
        instructions=prompt_ref["text"],
        output_type=MetadataResult,
    )

    async def task(item):
        return await extraction_task(
            dataset_item={"input": item.input, "expected_output": item.expected_output},
            agent=agent,
            extractor=extractor,
        )

    result = client.run_experiment(
        name=run_name or EXPERIMENT_NAME,
        description="Extract and evaluate document metadata",
        data=dataset_items,
        metadata={
            "dataset_name": DATASET_NAME,
            "model": os.getenv("LLM"),
            "extractor": extractor,
            "prompt_name": prompt_ref["name"],
            "prompt_version": str(prompt_ref.get("version")),
            "pages": "1,2",
        },
        task=task,
        evaluators=[item_summary_evaluator],
        run_evaluators=[average_score_evaluator],
    )

    print(result.format())
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run metadata extraction experiment.")
    parser.add_argument(
        "--model", default=os.getenv("LLM"), help="LLM model, e.g. litellm/gpt-4o"
    )
    parser.add_argument(
        "--extractor", default="pdfplumber", help="PDF extractor (default: pdfplumber)"
    )
    parser.add_argument(
        "--prompt", default="medium", help="Prompt name (default: medium)"
    )
    args = parser.parse_args()

    if args.model:
        os.environ["LLM"] = args.model

    asyncio.run(run(extractor=args.extractor, prompt_name=args.prompt))
