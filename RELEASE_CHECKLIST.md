# CivicOS — GitHub Release Checklist

## Before Pushing to GitHub

### Code Quality
- [x] Ruff lint: 0 errors
- [x] All tests pass (31 integration + unit tests)
- [x] Demo pipeline runs end-to-end (13 programs from 3 live sources)
- [x] TypeScript SDK compiles with strict mode
- [x] No hardcoded secrets (all via .env)
- [x] No `console.log` (all structlog)

### Documentation
- [x] README.md with quick start, architecture, API table
- [x] CONTRIBUTING.md with development setup
- [x] CHANGELOG.md following Keep a Changelog
- [x] LICENSE (MIT)
- [x] .env.example (no real keys)
- [x] Subpackage READMEs (6 packages documented)
- [x] Docusaurus docs site (intro, quickstart, architecture, API, guides)

### Repository Hygiene
- [x] .gitignore (Python, Node, IDE, OS, Docker, env)
- [x] .dockerignore
- [x] docker-compose.yml (one-command setup)
- [x] Dockerfile for API
- [x] CI/CD workflow (GitHub Actions)
- [x] CVE research starter kit (cve-research/)
- [x] demo_report.json showing verified results

### Version Check
- [x] pyproject.toml version: 0.1.0
- [x] SDK pyproject.toml version: 0.1.0
- [x] SDK package.json version: 0.1.0
- [x] All versions consistent

### Git Setup Commands

```bash
cd civicos

# Initialize git
git init
git add .
git commit -m "feat: initial CivicOS v0.1.0 release

Complete end-to-end pipeline:
- Ingestion: httpx + Playwright scraper, pdfminer PDF parser
- Extraction: Claude API client + mock rule-based fallback
- Storage: PostgreSQL 16 with JSONB, tsvector search, trigger versioning
- API: FastAPI with 10 endpoints, filtering, pagination, search
- SDKs: Python (pip) and TypeScript (npm) client libraries
- CLI: civicos seed, scrape, extract, ingest, serve
- CI/CD: GitHub Actions with lint, type-check, and tests
- Docs: Docusaurus site with architecture, API reference, guides

Demo verified: 13 programs extracted from 3 live Boston.gov sources."

# Create GitHub repo
gh repo create civicos --public --source=. --push

# Or manually:
# 1. Create repo on GitHub (don't initialize with README)
# 2. git remote add origin https://github.com/Yeisbel/civicos.git
# 3. git branch -M main
# 4. git push -u origin main
```

### Post-Push Actions

- [ ] Verify CI passes (GitHub Actions)
- [ ] Verify README renders correctly
- [ ] Tag v0.1.0: `git tag v0.1.0 && git push --tags`
- [ ] Write dev.to post: "How I built an LLM pipeline to extract structured data from government PDFs"
- [ ] Post to Hacker News: "Show HN: CivicOS — open-source civic data API"
- [ ] Share in Code for America Slack
- [ ] Add real ANTHROPIC_API_KEY to your deployment
- [ ] Set up GitHub branch protection rules

### Next Development Phase (v0.2)

- [ ] Add 5 more Boston data sources (food, healthcare, legal categories)
- [ ] Implement proper change detection diff (program_versions trigger refinement)
- [ ] Add Celery/RQ background workers for ingestion
- [ ] SDK tests (Python + JS)
- [ ] Deploy to fly.io or Railway for live demo
- [ ] Begin CVE research: study 10 CVEs, install fuzzing toolchain
