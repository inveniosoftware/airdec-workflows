# SPDX-FileCopyrightText: 2026 CERN.
# SPDX-License-Identifier: MIT

"""Langfuse experiments runner using the SDK Experiments API."""

import argparse
import asyncio
import os
from pathlib import Path

from dataset import (
    get_or_create_langfuse_dataset,
    load_local_dataset,
)
from dataset_sync import sync_dataset
from evaluators import (
    average_score_evaluator,
    build_comparison_payload,
    item_summary_evaluator,
)
from langfuse import get_client
from prompts import sync_extraction_prompt

from app.activities.extract_metadata import extract_metadata_record
from app.config import get_settings
from app.extractors import get_extractor

DATASET_NAME = "orcha-eval-dataset"
DEFAULT_EXPERIMENT_NAME = "dataset"
MAX_CONCURRENT_REQUESTS = 4
RETRYABLE_HTTP_STATUS_CODES = {429, 500, 502, 503, 504}


async def _with_retry(call, *, retries: int = 3, base_delay: float = 1.0):
    """Retry LLM calls that fail with transient HTTP errors."""
    for attempt in range(retries):
        try:
            return await call()
        except Exception as exc:
            status_code = getattr(exc, "status_code", None)
            if attempt == retries - 1 or status_code not in RETRYABLE_HTTP_STATUS_CODES:
                raise
            await asyncio.sleep(base_delay * (2**attempt))


def save_extracted_text(text: str, record_id: str, dataset_root: Path) -> None:
    """Save extracted text to a file in the extracted_text directory for inspection."""
    extracted_dir = dataset_root / "extracted_text"
    extracted_dir.mkdir(parents=True, exist_ok=True)

    output_path = extracted_dir / f"{record_id}.txt"
    output_path.write_text(text, encoding="utf-8")


async def extraction_task(
    dataset_item,
    dataset_root: Path,
    extractor_name: str = "pdfplumber",
):
    """Extract text, run the agent, and build evaluator comparison data."""
    input_data = dataset_item.get("input")
    pdf_path = Path(input_data.get("pdf_path"))
    expected = dataset_item.get("expected_output")
    record_id = input_data.get("record_id") or pdf_path.stem

    extractor = get_extractor(extractor_name)
    pdf_bytes = pdf_path.read_bytes()
    text = extractor.extract(pdf_bytes, pages=[1, 2])["full_text"]
    save_extracted_text(text, record_id, dataset_root)

    # Reuse the app's metadata helper without going through Temporal.
    metadata = await _with_retry(lambda: extract_metadata_record(text))
    output_dict = metadata.model_dump(mode="json")
    output_dict["comparison"] = build_comparison_payload(output_dict, expected)

    return {
        "pdf_filename": pdf_path.name,
        "comparison": output_dict["comparison"],
    }


async def run(
    extractor: str = "pdfplumber",
    prompt_name: str = "prompt",
):
    """Run extraction and evaluation experiment."""
    dataset_root, provenance = sync_dataset(ref="main")
    items = load_local_dataset(dataset_root, DATASET_NAME)

    client = get_client()
    prompt_ref = sync_extraction_prompt(client, prompt_name)

    dataset_items = get_or_create_langfuse_dataset(
        client,
        DATASET_NAME,
        items,
    )
    settings = get_settings()

    async def task(item):
        return await extraction_task(
            dataset_item={
                "input": item.input,
                "expected_output": item.expected_output,
            },
            dataset_root=dataset_root,
            extractor_name=extractor,
        )

    effective_run_name = f"{extractor}__{settings.llm}"

    result = client.run_experiment(
        name=effective_run_name,
        description="Extract and evaluate document metadata",
        data=dataset_items,
        metadata={
            "dataset_name": DATASET_NAME,
            "model": settings.llm,
            "extractor": extractor,
            "prompt_name": prompt_ref["name"],
            "prompt_version": str(prompt_ref.get("version")),
            "pages": "1,2",
        },
        task=task,
        evaluators=[item_summary_evaluator],
        run_evaluators=[average_score_evaluator],
        max_concurrency=MAX_CONCURRENT_REQUESTS,
    )

    print(result.format())
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run metadata extraction experiment.")
    parser.add_argument("--model", default=os.getenv("LLM"), help="LLM model")
    parser.add_argument(
        "--extractor", default="pdfplumber", help="PDF extractor (default: pdfplumber)"
    )
    parser.add_argument(
        "--prompt", default="prompt", help="Prompt name (default: prompt)"
    )
    args = parser.parse_args()

    if args.model:
        os.environ["LLM"] = args.model

    asyncio.run(run(extractor=args.extractor, prompt_name=args.prompt))
