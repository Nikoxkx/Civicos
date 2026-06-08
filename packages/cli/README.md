# CivicOS CLI

**Command-line interface for managing the CivicOS platform.**

```bash
pip install -e ".[dev]"
```

## Commands

```bash
# Seed the database with cities and categories
civicos seed

# Scrape a URL and display extracted text
civicos scrape --url https://www.boston.gov/departments/housing/...

# Scrape + extract programs from a URL
civicos extract --url https://www.boston.gov/...

# Ingest all sources for a city (scrape → extract → store)
civicos ingest --city boston

# Start the API server
civicos serve

# Start on custom port
civicos serve --port 3000
```

## Example Workflow

```bash
# 1. Seed database
civicos seed

# 2. Test scraping on a single page
civicos scrape --url https://www.boston.gov/departments/housing/our-work-neighborhood-development

# 3. Test full extraction pipeline
civicos extract --url https://www.boston.gov/departments/housing/our-work-neighborhood-development

# 4. Ingest all registered Boston sources
civicos ingest --city boston

# 5. Start the API
civicos serve
```
