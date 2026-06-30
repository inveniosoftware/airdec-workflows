# Changelog

## [Unreleased]

### Features
- *(tracking)* Add created, starttime, endtime to workflows, needed for KPIs
- Helm chart v0.2.1
  - Add database migration job, langfuse secrets, and make the worker deployment's replicas configurable

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

[unreleased]: https://github.com/inveniosoftware/orcha/compare/v0.1.3...HEAD
[0.1.3]: https://github.com/inveniosoftware/orcha/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/inveniosoftware/orcha/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/inveniosoftware/orcha/compare/v0.0.1...v0.1.1
[0.0.1]: https://github.com/inveniosoftware/orcha/releases/tag/v0.0.1
