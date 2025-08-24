# Repo Inventory

## Overview

- **Project**: Agentic blog writer
- **Purpose**: Multi‑agent workflow that plans, researches, scrapes, synthesizes, and enhances blog articles. The orchestrator runs phases and invokes agents/tools via the OpenAI Agents SDK Runner [evidence: `app/workflows/article_creation_workflow.py:L25-L31`, `app/workflows/article_creation_workflow.py:L44-L53`, `app/workflows/article_creation_workflow.py:L140-L149`, `app/workflows/article_creation_workflow.py:L175-L186`].
- **Orchestrator**: `ArticleCreationWorkflow` coordinating planning → research → scraping → synthesis → finalization → Gemini enhancement [evidence: `app/workflows/article_creation_workflow.py:L55-L116`].
- **Models used**: Agents driven by model names from environment (e.g., `SMALL_REASONING_MODEL`, `LARGE_REASONING_MODEL`) and Google Gemini models via `google.genai` [evidence: `app/agents/planner_agent.py:L48-L56`, `app/agents/article_synthesizer_agent.py:L170-L178`, `app/services/gemini_enhancer.py:L2-L6`, `app/services/gemini_enhancer.py:L10-L16`].
- **Key libraries in code**: OpenAI Agents SDK (`agents`), google‑genai, httpx/requests, duckduckgo_search, Crawl4AI, Firecrawl, Newspaper4k, pydantic, python‑dotenv, rich [evidence: imports in `app/agents/common_imports.py:L1-L8`, `app/services/gemini_enhancer.py:L2-L6`, `app/tools/serper_websearch.py:L5-L13`, `app/tools/web_search_tool.py:L1-L6`, `app/services/web_scraping_service.py:L5-L7`, `app/tools/scraper.py:L3-L11`, `app/models/article_schemas.py:L1-L3`, `app/core/config.py:L3-L6`, `app/core/console_config.py:L6-L9`].
- **Deployment target**: Unknown (no server entrypoints found; FastAPI present as a dependency but unused in code) [evidence: no `FastAPI(` or routers found via search].

## Directory tree

```text
app/
  agents/
    article_brief_writer_agent.py    # tool for brief (referenced by planner) [planner_agent]
    planner_agent.py                 # plans sections; uses Agent with tools [L48-L57]
    research_agent.py                # performs web search via tool; Agent config [L108-L115]
    research_recovery_agent.py       # recovery instructions (improve section queries)
    section_research_agent.py        # per‑section research agent
    section_synthesizer_agent.py     # synthesizes section; calls editor tool [L12-L20,L48-L52]
    article_synthesizer_agent.py     # composes final article; Agent config [L170-L178]
    section_editor_agent.py          # editor agent used as tool [L11-L19,L56-L61]
    common_imports.py                # shared imports; hooks, Runner [L1-L8,L15-L17]
    hooks/custom_agent_hooks.py      # Agent lifecycle hooks [L10-L18]
  core/
    config.py                        # loads env; central config [L9-L23,L40-L61,L66-L78]
    console_config.py                # Rich console [L1-L9]
    logging_config.py                # logging via RichHandler [L11-L26,L45-L59]
    printer.py                       # live status printer [L8-L19,L26-L33,L38-L46]
  models/
    article_schemas.py               # pydantic models for plan/research/article [L4-L21,L27-L40,L45-L68]
    workflow_schemas.py              # dataclass for workflow config [L4-L9]
  services/
    workflow_display_manager.py      # print summaries [L7-L16,L31-L46]
    workflow_data_manager.py         # cache persist/load json [L12-L21,L22-L38,L39-L55]
    web_scraping_service.py          # scrape URLs via Crawl4AI [L9-L18,L106-L118,L120-L167]
    gemini_enhancer.py               # enhance using Gemini [L9-L16,L79-L88,L96-L102]
  tools/
    serper_websearch.py              # Serper Google Search API tool [L12-L15,L17-L25,L66-L73]
    web_search_tool.py               # DuckDuckGo search tool [L11-L16,L37-L40]
    bing_websearch.py                # Bing Web Search API tool [L11-L19,L34-L43,L58-L72]
    scraper.py                       # Firecrawl, Newspaper4k, Crawl4AI tools [L10-L14,L27-L33,L51-L57,L73-L91]
    custom_tools.py                  # placeholder (empty)
  workflows/
    article_creation_workflow.py     # main orchestrator & __main__ [L25-L31,L44-L53,L55-L116,L607-L615]
cli/
  main.py                            # placeholder (empty)
  commands/generate_article.py       # placeholder (empty)
docs/
  cantons_run_inputs.txt             # sample inputs file
scripts/                             # empty
tests/                               # skeleton packages
```

All descriptions above derive from docstrings/comments or obvious usage in code files cited inline.

## Entrypoints

- **Workflow script (interactive)**: `python app/workflows/article_creation_workflow.py` prompts for title/description/layout/wordcount and runs the workflow [evidence: `app/workflows/article_creation_workflow.py:L596-L606`, `app/workflows/article_creation_workflow.py:L607-L615`].
- **Gemini enhancer demo**: `python app/services/gemini_enhancer.py` runs an example generation (for demonstration) [evidence: `app/services/gemini_enhancer.py:L104-L118`].
- **CLI package**: present but not implemented; `cli/main.py` and `cli/commands/generate_article.py` are empty [evidence: `cli/main.py:L1-L1`, `cli/commands/generate_article.py:L1-L1`].
- **API server**: Unknown; no FastAPI app/routers found in code despite dependency presence [evidence: repository‑wide search returned no `FastAPI(` or `APIRouter(`].
- **Notebooks/Jobs**: None found in repo.

## Dependencies (used in code)

- **OpenAI Agents SDK**: `agents` imported for `Agent`, `Runner`, tools and tracing; orchestrates agent runs [evidence: `app/agents/common_imports.py:L5-L8,L11`, `app/workflows/article_creation_workflow.py:L9`, `app/tools/*:L1-L2,L5`]. Listed as `openai-agents` dependency [evidence: `requirements.txt:L66`, `pyproject.toml:L6`].
- **google‑genai**: Gemini client/models/types for enhancement [evidence: `app/services/gemini_enhancer.py:L2-L6,L10-L16`].
- **Search/HTTP**: `httpx` (async Serper) and `requests` (Bing) [evidence: `app/tools/serper_websearch.py:L7-L8,L66-L71`, `app/tools/bing_websearch.py:L3,L58-L72`].
- **DuckDuckGo search**: `duckduckgo_search.DDGS` [evidence: `app/tools/web_search_tool.py:L1,L37-L40`].
- **Scraping**: Crawl4AI and Firecrawl; Newspaper4k article extraction [evidence: `app/services/web_scraping_service.py:L5-L7,L120-L167`, `app/tools/scraper.py:L3,L10-L14,L27-L33,L73-L91`].
- **Data/validation**: pydantic BaseModel; dataclasses [evidence: `app/models/article_schemas.py:L1-L3`, `app/models/workflow_schemas.py:L1-L9`].
- **Runtime UX**: rich console/logging/printer [evidence: `app/core/console_config.py:L6-L9`, `app/core/logging_config.py:L11-L26`, `app/core/printer.py:L8-L19`].
- Additional packages exist in `pyproject.toml`/`requirements.txt` (e.g., FastAPI, uvicorn), but no import usage was found in this codebase.

## Config & Secrets

- **Configuration loader**: `app/core/config.py` loads `.env` at import time and exposes attributes; validates required keys [evidence: `app/core/config.py:L3-L6`, `app/core/config.py:L39-L47`, `app/core/config.py:L66-L78`, `app/core/config.py:L95-L96`].
- **Environment variables (read in code)**:
  - API keys: `OPENAI_API_KEY`, `GEMINI_API_KEY`, `FIRECRAWL_API_KEY`, `SERPER_API_KEY`, `BING_SEARCH_V7_SUBSCRIPTION_KEY`, `BING_SEARCH_V7_ENDPOINT` [evidence: `app/core/config.py:L40-L41,L56`, `app/tools/serper_websearch.py:L12-L15`, `app/tools/bing_websearch.py:L34-L39`, `app/tools/scraper.py:L10`].
  - Model names: `LARGE_REASONING_MODEL`, `SMALL_REASONING_MODEL`, `SMALL_FAST_MODEL`, `LARGE_FAST_MODEL`, `IMAGE_GENERATION_MODEL`, `GEMINI_FLASH_MODEL`, `GEMINI_FLASH_PRO_MODEL` [evidence: `app/core/config.py:L44-L51`].
  - Behavior/logging: `RESEARCH_STRATEGY`, `RESEARCH_MAX_RETRIES`, `LOGGING_LEVEL` [evidence: `app/core/config.py:L53,L59-L61`].
  - Search region: `DDG_REGION` [evidence: `app/tools/web_search_tool.py:L38`].
- **.env handling**: `dotenv.load_dotenv()` used in config and tools [evidence: `app/core/config.py:L3-L6`, `app/tools/serper_websearch.py:L4,L10`, `app/tools/bing_websearch.py:L6,L9`, `app/tools/web_search_tool.py:L4,L9`].

## External Services

- **OpenAI Agents platform**: Agents and Runner orchestrate reasoning/tools; `trace`/`gen_trace_id` are used to link to OpenAI Traces UI [evidence: `app/workflows/article_creation_workflow.py:L9`, `app/workflows/article_creation_workflow.py:L45-L49`, `app/services/workflow_display_manager.py:L23-L29`]. Credentials via `OPENAI_API_KEY` [evidence: `app/core/config.py:L40`].
- **Google Gemini**: Content enhancement with Google Search grounding tools via `google.genai` [evidence: `app/services/gemini_enhancer.py:L2-L6,L80-L86,L96-L102`]. Credentials via `GEMINI_API_KEY` and model envs [evidence: `app/services/gemini_enhancer.py:L10-L16`, `app/core/config.py:L41,L49-L51`].
- **Serper (Google Search API)**: `https://google.serper.dev/search` used with `SERPER_API_KEY` [evidence: `app/tools/serper_websearch.py:L48-L56,L57-L60,L12-L15`].
- **Bing Web Search API**: endpoint+subscription key envs; REST via `requests` [evidence: `app/tools/bing_websearch.py:L34-L39,L58-L72`].
- **DuckDuckGo (library)**: local search via `duckduckgo_search` (no API key) [evidence: `app/tools/web_search_tool.py:L1,L37-L40`].
- **Crawl4AI**: browser‑driven scraping for research URLs [evidence: `app/services/web_scraping_service.py:L106-L118,L120-L167`].
- **Firecrawl**: content scrape via SDK [evidence: `app/tools/scraper.py:L3,L10-L14,L27-L33`].
- **Newspaper4k**: article text extraction [evidence: `app/tools/scraper.py:L5,L51-L57`].

## Architecture

```mermaid
graph TD
  A[ArticleCreationWorkflow
  app/workflows/article_creation_workflow.py] -->|Runner.run| P[Planner Agent
  app/agents/planner_agent.py]
  A --> R[Research Agent
  app/agents/research_agent.py]
  A --> S[Section Synthesizer
  app/agents/section_synthesizer_agent.py]
  A --> F[Final Article Synthesizer
  app/agents/article_synthesizer_agent.py]
  A --> G[Gemini Enhancer
  app/services/gemini_enhancer.py]
  A --> WDM[WorkflowDataManager
  app/services/workflow_data_manager.py]
  A --> WDisp[WorkflowDisplayManager
  app/services/workflow_display_manager.py]
  R -->|tool| Serper[Serper Search Tool
  app/tools/serper_websearch.py]
  R -. optional .->|tool| DDG[DDG Search Tool
  app/tools/web_search_tool.py]
  A --> Scrape[WebScrapingService
  app/services/web_scraping_service.py]
  Scrape --> Crawl4AI[Crawl4AI]
  Scrape -. alt .-> Firecrawl[Firecrawl]
  Serper --> SerperAPI[(serper API)]
  G --> Gemini[(Google Gemini)]
  DDG --> Duck[(duckduckgo_search)]
  Bing[Bing Web Search Tool
  app/tools/bing_websearch.py] --> BingAPI[(Bing Web Search)]
```

## Evidence table

| Filepath | Purpose | Code lines |
|---|---|---|
| `app/workflows/article_creation_workflow.py` | Orchestrates multi‑phase article creation; uses Runner; interactive entrypoint | L25-L31, L44-L53, L55-L116, L140-L149, L175-L186, L596-L615 |
| `app/agents/common_imports.py` | Centralizes Agent/Runner/hook imports; defines quiet/verbose hooks | L1-L8, L15-L17 |
| `app/agents/planner_agent.py` | Planner Agent configured with model and tools | L48-L57 |
| `app/agents/research_agent.py` | Research Agent calls Serper tool; model and hooks | L108-L115 |
| `app/agents/section_synthesizer_agent.py` | Section synthesis Agent; uses editor tool | L12-L20, L48-L52 |
| `app/agents/article_synthesizer_agent.py` | Final article Agent; uses LARGE model | L170-L178 |
| `app/agents/section_editor_agent.py` | Editor Agent to refine text | L11-L19, L56-L61 |
| `app/models/article_schemas.py` | Pydantic schemas for plans/research/article | L4-L21, L27-L40, L45-L68 |
| `app/models/workflow_schemas.py` | Workflow config dataclass | L4-L9 |
| `app/services/workflow_data_manager.py` | JSON cache save/load/clear | L12-L21, L22-L38, L39-L55, L81-L101 |
| `app/services/workflow_display_manager.py` | Printing of summaries and status | L7-L16, L31-L46, L48-L63, L65-L83, L84-L104, L105-L123, L124-L149 |
| `app/services/web_scraping_service.py` | Extract URLs, scrape via Crawl4AI, update notes | L9-L18, L39-L50, L82-L91, L106-L118, L120-L167, L190-L203, L204-L223 |
| `app/services/gemini_enhancer.py` | Enhance article with Google Gemini | L2-L6, L9-L16, L79-L88, L96-L102, L104-L118 |
| `app/tools/serper_websearch.py` | Serper Google Search API tool | L12-L15, L17-L25, L48-L56, L57-L60, L66-L73 |
| `app/tools/bing_websearch.py` | Bing Web Search API tool | L11-L19, L34-L43, L58-L72 |
| `app/tools/web_search_tool.py` | DuckDuckGo search tool with throttling | L11-L16, L37-L40 |
| `app/tools/scraper.py` | Firecrawl, Newspaper4k, Crawl4AI scraping tools | L10-L14, L24-L33, L51-L57, L73-L91 |
| `app/core/config.py` | Loads `.env`, exposes env config, validates keys | L3-L6, L9-L23, L39-L47, L44-L61, L66-L78, L81-L93, L95-L96 |
| `app/core/console_config.py` | Rich console singleton | L1-L9 |
| `app/core/logging_config.py` | Configure Rich logging | L11-L26, L45-L59 |
| `app/core/printer.py` | Live status printer | L8-L19, L26-L33, L38-L46 |
| `cli/main.py` | Placeholder (empty) | L1-L1 |
| `cli/commands/generate_article.py` | Placeholder (empty) | L1-L1 |

Notes:
- “Unknown” items (e.g., deployment target) indicate no confirming code evidence found.


