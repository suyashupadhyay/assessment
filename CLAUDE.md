# CLAUDE.md — Assessment Repository Guide

This file provides AI assistants with a complete map of this repository's structure, conventions, and workflows.

---

## Project Overview

This repository is a **Python utility and tools workspace** that started as a minimal execution-timing utility and is being expanded into a **Creative Intelligence Agent** for performance marketing — a modular system for scraping, analyzing, and generating ad creative insights.

---

## Repository Structure

```
assessment/
├── CLAUDE.md                          # This file
├── measure_execution_time.py          # Original utility: execution time helpers
└── creative_intelligence/             # Module suite for performance marketing
    └── module1_meta_scraper/          # Module 1: Meta Ad Library Scraper
        ├── meta_ad_scraper.py         # Main scraper script
        ├── .env.example               # Template for environment variables
        └── requirements.txt           # Python dependencies
```

---

## Language & Runtime

- **Language**: Python 3.x (no specific version pinned; use 3.8+ for f-string and walrus operator compatibility)
- **Standard library only** for the core utility (`time`, `functools`)
- **Third-party deps** only where explicitly required (see per-module `requirements.txt`)

---

## Modules

### `measure_execution_time.py`

A standalone timing utility. No dependencies beyond the standard library.

**Public API:**

| Symbol | Type | Description |
|---|---|---|
| `measure_time(func)` | Decorator | Wraps a function; prints `<name> took X.XXXXXX seconds` on each call |
| `time_it(func, *args, **kwargs)` | Function | Calls `func(*args, **kwargs)`; returns `(result, elapsed_seconds)` |

**Usage:**
```python
from measure_execution_time import measure_time, time_it

@measure_time
def my_func():
    ...

result, elapsed = time_it(sorted, [3, 1, 4, 1, 5])
```

**Implementation notes:**
- Uses `time.perf_counter()` for high-resolution, monotonic timing
- `measure_time` uses `functools.wraps` to preserve the wrapped function's `__name__`, `__doc__`, etc.
- `time_it` does **not** print; callers receive raw elapsed time for programmatic use

---

### `creative_intelligence/module1_meta_scraper/`

A scraper for the Meta Ad Library API. See that module's own README/comments for full usage.

**Key file**: `meta_ad_scraper.py`

**Inputs (CLI or prompts):**
- `search_query` — brand/category keyword (e.g., `"astrotalk"`, `"edtech"`)
- `country` — ISO country code, default `IN`

**Output:**
- `{search_query}_ads_raw.json` — structured ad data
- Terminal summary (totals, media breakdown, profitable ads, top pages)

**Environment variable required:**
```
META_ACCESS_TOKEN=<your_token>   # stored in .env (never commit the real .env)
```

---

## Development Conventions

### Code Style

- Follow **PEP 8** (4-space indentation, max 99 chars per line)
- Prefer **f-strings** over `.format()` or `%`-formatting
- Use **type hints** on public functions when adding new code
- Docstrings: Google-style or one-line summary for simple functions

### Naming

| Thing | Convention | Example |
|---|---|---|
| Functions / variables | `snake_case` | `measure_time`, `elapsed` |
| Classes | `PascalCase` | `AdRecord` |
| Constants / env vars | `UPPER_SNAKE_CASE` | `META_ACCESS_TOKEN` |
| Files / modules | `snake_case` | `meta_ad_scraper.py` |

### Error Handling

- Always handle HTTP errors explicitly (check `response.status_code`, use `response.raise_for_status()`)
- Catch `requests.exceptions.RequestException` at the top-level call site
- Print human-readable error messages; do not swallow exceptions silently
- For API rate limits: implement exponential back-off before retrying

### Secrets & Configuration

- **Never hard-code** tokens, keys, or secrets in source files
- Store secrets in `.env`; load with `python-dotenv`
- Commit only `.env.example` (with placeholder values); add `.env` to `.gitignore`

### Pagination

- When calling paginated APIs, always follow `next` cursors/page tokens until exhausted or a cap is reached
- Document the cap clearly (e.g., `MAX_ADS = 200`)

---

## Running the Code

### Execution timing utility

```bash
python measure_execution_time.py
```

No setup required.

### Meta Ad Scraper

```bash
cd creative_intelligence/module1_meta_scraper
pip install -r requirements.txt
cp .env.example .env          # then fill in META_ACCESS_TOKEN
python meta_ad_scraper.py
```

---

## Git Workflow

- **Active development branch**: `claude/claude-md-mm4zztcvtwi46anv-7y1Rd`
- **Base branch**: `master`
- Push with: `git push -u origin <branch-name>`
- Commit messages: imperative mood, concise subject line (≤72 chars), e.g. `Add Meta Ad Library scraper (Module 1)`

---

## No Build / No CI (current state)

- No Makefile, no Docker, no CI pipeline exists yet
- No test suite — add `pytest`-based tests under `tests/` if/when the project grows
- No linter config — apply `black` + `flake8` manually if desired

---

## Key Decisions & Rationale

| Decision | Rationale |
|---|---|
| `time.perf_counter()` over `time.time()` | Monotonic, higher resolution; unaffected by system clock changes |
| `functools.wraps` in decorator | Preserves introspection (`__name__`, `__doc__`) of wrapped functions |
| Separate `time_it` function alongside decorator | Enables timing of third-party callables without modifying their source |
| `.env` + `python-dotenv` for secrets | Keeps credentials out of version control; portable across environments |
| 30-day threshold for `likely_profitable` | Industry heuristic: advertisers rarely keep unprofitable ads running beyond a month |

---

## What AI Assistants Should Know

1. **Read this file first** before making changes — it reflects the current state of the repo.
2. The repo is intentionally minimal; avoid adding unnecessary boilerplate or frameworks.
3. When adding a new module, create it under `creative_intelligence/module<N>_<name>/` and update this file.
4. All secrets go in `.env`, never in committed code.
5. Prefer editing existing files over creating new ones unless a new module or file type is genuinely needed.
6. After any significant addition, update the **Repository Structure** and **Modules** sections above.
