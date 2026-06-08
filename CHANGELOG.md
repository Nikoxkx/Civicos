# Changelog

All notable changes to CivicOS will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] — 2026-06-08

### Added

#### Core Platform
- **API Server** (FastAPI): 10 REST endpoints with filtering, pagination, full-text search, and structured error handling
- **Database Schema**: 6 tables (cities, categories, programs, program_versions, sources, ingestion_runs) with JSONB flexibility, GIN indexes, and trigger-based versioning
- **Web Scraper** (httpx + Playwright): Dual-mode scraping with auto-fallback for JS-rendered pages
- **PDF Parser** (pdfminer.six): Layout-aware text extraction from government PDFs
- **Extraction Pipeline**: Claude API client with exponential backoff retry + mock rule-based fallback for dev/CI
- **CLI** (click): `civicos seed`, `civicos scrape`, `civicos extract`, `civicos ingest`, `civicos serve`

#### SDKs
- **Python SDK** (`civicos`): pip-installable client with programs, cities, categories, search modules
- **TypeScript SDK** (`civicos-sdk`): npm package with full type definitions

#### Documentation
- **Docusaurus site**: architecture overview, extraction pipeline docs, API reference, guides
- **Subpackage READMEs**: api, db, ingestion, extraction, cli, sdk-js, sdk-py
- **Demo script**: End-to-end pipeline with real Boston.gov data (3 sources → 13 programs)

#### Developer Experience
- **Docker Compose**: One-command PostgreSQL + API setup
- **CI/CD** (GitHub Actions): lint + type-check + test on push/PR
- **Tests**: 31 tests across API, scraper, extraction, PDF parser, and integration
- **Ruff linting**: Zero errors with configured ignore rules for intentional patterns

#### Data
- **Boston seed data**: City record, 9 categories, 2 initial data sources
- **Demo verified**: 13 programs extracted from 3 live Boston.gov sources, stored and API-verified

### Architecture Decisions

- UUIDs for all public IDs (not serial) — prevents enumeration, enables distributed generation
- JSONB for eligibility_json and program_versions.diff — flexible schemas without migrations
- GENERATED tsvector for full-text search — zero external infrastructure
- Raw HTML preserved alongside extracted text — enables re-extraction with improved models
- Mock extraction as fallback — enables CI/CD without API costs
- Synchronous ingestion in v0.1 — background workers deferred to v0.3
- No authentication in v0.1 — designed for self-hosted deployments behind reverse proxy
