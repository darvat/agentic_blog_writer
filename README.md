# Agentic Blog Writer

Agentic Blog Writer is a multi-agent content production pipeline that plans, researches, writes, and post-processes long-form blog posts. The project wraps OpenAI- and Gemini-powered specialists inside an orchestrated workflow, complementing LLM output with structured research, web scraping, and SEO-focused polishing.

## Key Capabilities
- Multi-phase workflow: planning, research, web scraping, section synthesis, final assembly, and Gemini enhancement.
- Agent hierarchy with interchangeable models and auto-reflection hooks to improve reliability.
- Cached intermediate artifacts under `data/<slug>` to make re-runs idempotent and debuggable.
- Research enrichment via DuckDuckGo, Bing, Serper, and optional web crawling using `crawl4ai`.
- Rich-console progress UI, persistent JSON logs, and Google Gemini-based fact-checking with structured prompts.

## Architecture
- **Workflows (`app/workflows/`)** – `article_creation_workflow.py` orchestrates the full lifecycle, coordinates persistence, and owns retry logic and recovery flows.
- **Agents (`app/agents/`)** – Pydantic-first agent definitions for planning, research, section synthesis, and article assembly. Agents share utilities from `common_imports.py` and can expose themselves as tools to other agents.
- **Services (`app/services/`)** – Operational helpers for output streaming (`Printer`), cached storage (`WorkflowDataManager`), status reporting (`WorkflowDisplayManager`), Gemini enhancement, and async crawling.
- **Models (`app/models/`)** – Typed schemas (Pydantic models and dataclasses) that define inputs/outputs for every phase, ensuring agents exchange structured data.
- **Tools (`app/tools/`)** – Search adapters (DuckDuckGo, Bing, Serper) registered as function tools, plus scraping helpers for agent calls.
- **CLI (`cli/`)** – Placeholder command group intended to wrap workflows; currently minimal and ready for expansion.

```
┌──────────┐     ┌────────────┐     ┌──────────────┐
│ Planner  │ ─▶ │ Researchers │ ─▶ │ Web Scrapers │
└──────────┘     └────────────┘     └──────────────┘
       │                 │                    │
       ▼                 ▼                    ▼
  Section Plans     Research Notes      Augmented Notes
       │                 │                    │
       ▼                 ▼                    ▼
┌────────────┐     ┌─────────────┐     ┌────────────────┐
│ Synthesizer│ ─▶ │ Final Article│ ─▶ │ Gemini Enhancer │
└────────────┘     └─────────────┘     └────────────────┘
```

## Workflow Stages
1. **Planning** – `planner_agent` generates structured section plans and an article brief. Results are cached as `planning.json`.
2. **Researching** – Either batch (`research_agent`) or per-section (`section_research_agent`) research populates findings; recovery cycles use `research_recovery_agent` for query refinement.
3. **Web Scraping** – `WebScrapingService` deduplicates URLs, filters non-HTML assets, and enriches notes with scraped markdown.
4. **Section Synthesis** – `section_synthesizer_agent` transforms each plan + research bundle into narrative copy, orchestrated via `asyncio.gather` for concurrency.
5. **Final Assembly** – `article_synthesizer_agent` stitches synthesized sections into an SEO-ready article, capturing metadata, TOC, and references.
6. **Gemini Enhancement** – `gemini_enhancer.generate` fact-checks and uplifts the article with Google GenAI, keeping layout fidelity while expanding content depth.

Each stage persists JSON snapshots (see `app/services/workflow_data_manager.py`), enabling resume/retry behaviour without re-running upstream agents.

## Agent and Tooling Highlights
- Agents derive from the shared `agents` wrapper (see `app/agents/common_imports.py`), providing unified logging, model routing, and function-tool registration.
- Search tooling is throttled (`asyncio_throttle.Throttler`) to respect provider limits.
- Recovery logic (`ArticleCreationWorkflow._attempt_research_recovery`) generates improved queries when research fails, ensuring graceful degradation.
- `Runner.run` centralises agent invocation with configurable `max_turns`, making it easy to adjust reasoning depth per phase.

## Services & Observability
- `Printer` + `WorkflowDisplayManager` build a Rich-powered live console, surfacing progress, summaries, and trace URLs.
- `app/core/logging_config.py` configures Rich logging handlers and lowers verbosity on chatty libraries.
- Gemini enhancement logs via `get_logger` and constrains output to markdown for downstream consumption.

## Data & Storage
- Workflow outputs live under `data/<title-slug>/` as phase-specific JSON files (e.g., `planning.json`, `researching.json`).
- The data manager gracefully handles schema evolution by validating cached payloads against the current Pydantic types.
- Additional research corpora, prompts, or scraped artifacts can be staged in `data/` for offline review.

## Getting Started
1. **Python** – Install Python 3.10 or newer.
2. **Virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```
3. **Dependencies** – Choose one of the available workflows:
   - `pip install -r requirements.txt`
   - or, if you use [uv](https://github.com/astral-sh/uv): `uv sync`
4. **Environment** – Copy `.env.example` (if available) or create `.env` with the required API keys (see below).

## Environment Configuration
| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes | Used by planner, research, synthesis, and article agents via OpenAI APIs. |
| `GEMINI_API_KEY` | Yes | Required for the Gemini enhancement service. |
| `LARGE_REASONING_MODEL` | Yes | e.g. `gpt-4o`. Used for planning and synthesis agents. |
| `SMALL_REASONING_MODEL` | Yes | Smaller reasoning model for lighter agents. |
| `SMALL_FAST_MODEL` / `LARGE_FAST_MODEL` | Optional | Override defaults for summarisation or fallback agents. |
| `GEMINI_FLASH_MODEL` / `GEMINI_FLASH_PRO_MODEL` | Optional | Gemini model names for enhancement. |
| `FIRECRAWL_API_KEY` | Optional | Enables Firecrawl-based scraping helpers. |
| `RESEARCH_STRATEGY` | Optional | Set to `batch` to use bulk research; defaults to `individual`. |
| `RESEARCH_MAX_RETRIES` | Optional | Retry budget for per-section research (defaults to 2). |
| `DDG_REGION` | Optional | Region filter for DuckDuckGo queries. |

> The configuration loader (`app/core/config.py`) validates required keys on import, so missing values will surface early.

## Running the Workflow
```bash
python -m app.workflows.article_creation_workflow
```
You will be prompted for the title, description, layout (optional), and word count. Workflow progress streams in the terminal, and all intermediate artifacts are written under `data/<slug>/`.

## Testing
- Run the existing test scaffold with `pytest` (tests are currently minimal and serve as a foundation for future coverage).
- Targeted testing recommendations:
  - Add unit tests for new agents to validate Pydantic schemas and tool wiring.
  - Introduce integration smoke tests that stub agent responses to exercise the workflow end-to-end without external API calls.

## Project Layout
```
app/
  agents/               # Planner, research, synthesis, recovery, and editing agents
  core/                 # Config, logging, console, and printer utilities
  models/               # Pydantic models for plans, research notes, and final articles
  services/             # Workflow orchestration helpers, data manager, Gemini enhancer, scraping
  tools/                # Search providers and custom agent tools
  workflows/            # Article creation workflow entry point
cli/                    # CLI scaffolding (ready for command registration)
data/                   # Cached workflow outputs and sample corpora
docs/                   # Project documentation and inventories
scripts/                # Utility scripts for operations and maintenance
tests/                  # Test scaffolding organised by domain (currently sparse)
```

## Roadmap Ideas
- Flesh out the CLI (`cli/main.py`, `cli/commands/`) to expose workflow presets and headless runs.
- Expand automated testing, especially around caching semantics and failure recovery paths.
- Add observability hooks (metrics/tracing) for long-running research and scraping stages.
- Generalise workflows to support multilingual or multi-format outputs (e.g., briefs, newsletters).

---
Feel free to file issues or proposals in `docs/` as the system evolves—the architecture is intentionally modular to accommodate new agents, data services, and publishing pipelines.
