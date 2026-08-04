# SPDX-FileCopyrightText: 2026 CERN.
# SPDX-License-Identifier: MIT

"""Run run.py across combinations of models, extractors, and prompts."""

import asyncio
import csv
import json
import os
from pathlib import Path

from run import run

RESULTS_DIR = Path("evals/sweep_results")

MODELS = ["litellm/openai/gpt-oss-20b"]

EXTRACTORS = ["pdfplumber", "pymupdf"]

PROMPTS = ["medium"]


def to_jsonable(obj):
    """Best-effort conversion of a result object to plain JSON-safe data."""
    if hasattr(obj, "model_dump"):  # pydantic v2
        return obj.model_dump(mode="json")
    if hasattr(obj, "dict"):  # pydantic v1
        return obj.dict()
    if hasattr(obj, "__dict__"):
        return {k: to_jsonable(v) for k, v in vars(obj).items()}
    if isinstance(obj, (list, tuple)):
        return [to_jsonable(v) for v in obj]
    if isinstance(obj, dict):
        return {k: to_jsonable(v) for k, v in obj.items()}
    return obj  # str, int, float, bool, None


def flatten_item_rows(run_name, model, extractor, prompt, result_data):
    """Pull out one row per dataset item, with whatever fields are present."""
    rows = []
    items = result_data.get("item_results") or result_data.get("items") or []
    for item in items:
        item = to_jsonable(item) if not isinstance(item, dict) else item
        output = item.get("output") or {}

        row = {
            "run_name": run_name,
            "model": model,
            "extractor": extractor,
            "prompt": prompt,
            "item_id": item.get("id") or item.get("item_id"),
            "pdf_filename": output.get("pdf_filename")
            if isinstance(output, dict)
            else None,
        }
        scores = item.get("scores") or item.get("evaluations") or []
        for score in scores:
            score = to_jsonable(score) if not isinstance(score, dict) else score
            name = score.get("name", "score")
            row[f"score__{name}"] = score.get("value")
        comparison = output.get("comparison") if isinstance(output, dict) else None
        if comparison:
            for k, v in comparison.items():
                row[f"comparison__{k}"] = v
        rows.append(row)
    return rows


async def run_sweep():
    """Run the configured evaluation sweep across models and extractors."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    all_item_rows = []

    for model in MODELS:
        for extractor in EXTRACTORS:
            for prompt in PROMPTS:
                os.environ["LLM"] = model
                run_name = f"{model.replace('/', '_')}__{extractor}__{prompt}"
                print(f"\n=== Running {run_name} ===")

                try:
                    result = await run(
                        extractor=extractor,
                        prompt_name=prompt,
                        run_name=run_name,
                    )
                    result_data = to_jsonable(result)

                    # Save full raw result as JSON (everything Langfuse gave us)
                    json_path = RESULTS_DIR / f"{run_name}.json"
                    json_path.write_text(json.dumps(result_data, indent=2, default=str))

                    # Try to flatten item-level rows for the combined CSV
                    all_item_rows.extend(
                        flatten_item_rows(
                            run_name, model, extractor, prompt, result_data
                        )
                    )

                except Exception as exc:
                    print(f"  ERROR: {exc}")
                    error_path = RESULTS_DIR / f"{run_name}_error.txt"
                    error_path.write_text(str(exc))

    # Write combined CSV across all runs, if we got any rows
    if all_item_rows:
        all_keys = sorted({k for row in all_item_rows for k in row})
        csv_path = RESULTS_DIR / "all_items.csv"
        with open(csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=all_keys)
            writer.writeheader()
            writer.writerows(all_item_rows)
        print(f"\nWrote {len(all_item_rows)} item rows to {csv_path}")
    else:
        print("\nNo item-level rows extracted — check the JSON files and result shape.")

    print(f"Full per-run JSON dumps in {RESULTS_DIR}")


if __name__ == "__main__":
    asyncio.run(run_sweep())
