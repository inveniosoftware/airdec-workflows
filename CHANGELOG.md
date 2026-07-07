# Changelog

## [Unreleased]

## [0.3.0] - 2026-07-07

### Features
- *(feedback)* Add workflow feedback flow
  - New `POST /workflows/{id}/feedback` endpoint to submit feedback on a workflow result

## [0.2.2] - 2026-07-07

### Features
- *(extract)* Reduce fabricated metadata suggestions
  - Tell the model to leave absent fields empty instead of using placeholders
  - Skip the LLM on near-empty text (<50 chars); image-only PDFs otherwise make the model fabricate records
  - Clear title/description/doi whose values aren't present in the source text

### Fixes
- *(schema)* Tighten extraction prompts so the model copies the source faithfully
  - Copy the abstract word-for-word instead of paraphrasing or shortening it
  - Include every author instead of truncating the list with et al.
  - Resolve each author's affiliation marker and drop the marker and postal address
- Stop falling back to the tenant id as the user id
- *(helm)* Keep the migration job and its logs after it finishes
  - Drop ttlSecondsAfterFinished so failed jobs and their logs aren't deleted
  - Drop hook-succeeded so a completed job stays until the next install or upgrade

### Refactor
- *(helm)* Extract shared db and langfuse env helpers

## [0.2.1] - 2026-07-02

### Fixes
- Install the langfuse extra in the Docker image

## [0.2.0] - 2026-07-02

### Features
- *(tracking)* Add created, starttime, endtime to workflows, needed for KPIs
- *(workflow)* Add user_id to workflows and context
- *(tracing)* Add optional Langfuse tracing
- *(helm)* Add database migration job and Langfuse secrets

### Fixes
- *(db)* Add unique constraint on public_id
- Limit retries per activity and workflow
- *(orcid)* Fix ORCID extraction and validation
  - Validate with idutils, shared by schema and extractor; drop IDs that fail the check digit
  - Flatten creators into parallel name/orcid/affiliation lists so gpt-oss keeps them in tool calls
  - Inline each ORCID next to its author and match the anchor by its position rather than the first substring match

### Refactor
- *(extractor)* Name the ORCID icon-matching tolerances
- *(helm)* Make worker replicas configurable

## [0.1.3] - 2026-06-29

### Features

- Configurable LLM settings via LLM_SETTINGS with more reliable extraction
  - LlmSettings parses the JSON LLM_SETTINGS env var: 
  model forwards to the chat model's request settings, output selects the structured-output strategy

### Fixes

- *(schema)* Keep YYYY-MM precision for publication dates
  - The validator collapsed YYYY-MM to YYYY; keep whatever precision is given
- *(extractor)* Stop flattening tables into full_text
  - Tables were re-appended as pipe-joined rows that duplicated page text and added empty-cell noise,
  bloating the prompt on dense documents. They remain in extra

### Refactor
- Add error logging for Orcha, providing more visibility on the errors in the terminal
- *(extraction)* Flat LLM schema with configurable output mode

## [0.1.2] - 2026-06-22

### Fixes
- Use valid sse framing

## [0.1.1] - 2026-06-17

### Features

- *(db)* Add alembic; initial migration
- *(helm)* Add initial chart for orcha
  - Added the Helm chart for deploying Orcha (with support for tenants)
  - Added deployment documentation (available in charts/orcha/README.md)

## [0.0.1] - 2026-06-09
_First release._

[unreleased]: https://github.com/inveniosoftware/orcha/compare/v0.2.2...HEAD
[0.3.0]: https://github.com/inveniosoftware/orcha/compare/v0.2.2...v0.3.0
[0.2.2]: https://github.com/inveniosoftware/orcha/compare/v0.2.1...v0.2.2
[0.2.1]: https://github.com/inveniosoftware/orcha/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/inveniosoftware/orcha/compare/v0.1.3...v0.2.0
[0.1.3]: https://github.com/inveniosoftware/orcha/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/inveniosoftware/orcha/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/inveniosoftware/orcha/compare/v0.0.1...v0.1.1
[0.0.1]: https://github.com/inveniosoftware/orcha/releases/tag/v0.0.1
