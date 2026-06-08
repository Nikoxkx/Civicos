---
sidebar_position: 1
slug: /intro
---

# CivicOS

**Open-source civic data intelligence platform.** CivicOS ingests government benefit and housing data from scattered websites and PDFs, uses LLMs to extract structured information, and exposes it all via a clean REST API.

---

## The Problem

Government benefit programs — housing assistance, food aid, healthcare subsidies — exist in every city. But the information lives across dozens of inconsistently formatted websites, PDFs, and outdated portals. The people who need these services most are the least equipped to navigate this fragmentation.

## What CivicOS Does

1. **Ingest** — Scrapes government websites and PDFs (Playwright + httpx)
2. **Extract** — Uses Claude or rule-based extraction to parse unstructured text into structured program data
3. **Store** — Normalized PostgreSQL schema with version history and change detection
4. **Serve** — REST API with filtering, search, and program history endpoints
5. **Monitor** — Detects when government pages change and flags what was updated

## Who This Is For

- **City governments** that want a resource navigator for their residents
- **Nonprofits** building community resource finders
- **Developers** who need structured civic data for apps
- **Researchers** studying government benefit accessibility

## The Story

CivicOS started in Dorchester, Boston. I watched my neighbors struggle to find housing assistance and food programs scattered across dozens of government URLs. I built DOR101 to solve it for my community. Then I realized every city has this problem — and almost no city has the engineering resources to build the extraction and normalization layer.

CivicOS is that layer, open-sourced, so any developer or city can deploy it and give their residents the same tool.

— **Bel**, Dorchester, Boston, MA