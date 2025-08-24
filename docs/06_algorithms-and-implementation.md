# Algorithms and Implementation

## Overview

This document describes the core algorithms and how they are implemented in the codebase, with precise citations to file:line ranges. It also summarizes heuristics, concurrency patterns, retries/timeouts, and error‑handling fallbacks, plus complexity/latency notes.

### Task Planning

High‑level: Check cache → run planner agent to produce `SectionPlans` (with `article_brief`) → persist.

Pseudo‑code:
```text
function plan_article(config):
  if cache.exists(planning):
    return cache.load(planning)

  result = Runner.run(planner_agent, input=config.title, context=config)
  plans = result.final_output_as(SectionPlans)
  cache.save(planning, plans)
  return plans
```

Implementation:
- Orchestrator planning: `app/workflows/article_creation_workflow.py:121-151`
- Planner agent instructions + tool wiring: `app/agents/planner_agent.py:12-46`, `app/agents/planner_agent.py:48-57`

Complexity and latency:
- Complexity: O(1) (single agent call); I/O bound on LLM latency.
- Typical latency: single model call (small reasoning model) + JSON parsing; cached runs are near‑instant.

### Outlining (Section Layout)

High‑level: If no layout provided, the planner first proposes a 3–5 section layout; otherwise it must adhere exactly to the supplied layout. Produces `SectionPlans` with `key_points` and optional `research_queries`.

Pseudo‑code:
```text
function outline(title, description, optional_layout):
  if optional_layout is empty:
    layout = LLM.generate_layout(3..5)
  else:
    layout = optional_layout

  sections = LLM.design_sections(title, description, layout)
  ensure sections strictly match layout if provided
  return sections
```

Implementation:
- Layout behavior and outlining requirements: `app/agents/planner_agent.py:15-27`, `app/agents/planner_agent.py:33-46`
- Output type (`SectionPlans`, `SectionPlan`): `app/models/article_schemas.py:12-21`

Complexity and latency:
- Complexity: O(1) (single agent prompt); LLM latency bound.
- Latency: small model; tens of seconds typical.

### Ranking

High‑level: Findings include a `relevance_score` field but ranking is not currently computed; results keep source order from search tools. Future work can score snippets and sort within section.

Pseudo‑code (planned):
```text
function rank_findings(findings):
  for f in findings:
    f.relevance_score = score(snippet=f.snippet, query=context_query)
  return sort(findings by relevance_score desc)
```

Current implementation state:
- Schema placeholder: `app/models/article_schemas.py:27-31` (has `relevance_score: Optional[float]`)
- Agents output placeholder value: `app/agents/research_agent.py:69-83` (JSON spec shows `relevance_score: null`)
- No ranking pass implemented in orchestrator or services.

Complexity and latency (if implemented):
- Expected O(F) scoring per section; total O(∑ F_section). Latency depends on scoring method (local heuristic ≈ negligible; LLM‑based ≈ additional model calls).

### Section Writing (Synthesis per Section)

High‑level: For each section plan, pair with its research notes and invoke Section Synthesizer Agent. All sections run concurrently using asyncio.gather. Each section must pass through the Editor tool before returning.

Pseudo‑code:
```text
function synthesize_sections(section_plans, research_notes):
  if cache.exists(synthesize_sections):
    return cache.load()

  tasks = []
  for plan in section_plans:
    notes = research_notes[plan.id]
    tasks.append(Runner.run(section_synthesizer_agent, json(plan, notes)))

  results = await asyncio.gather(*tasks)
  sections = parse_successes(results)
  if sections.empty(): return None

  full_text_for_editing = join(sections.content, sep="\n\n---\n\n")
  cache.save(SythesizedArticle(sections, full_text_for_editing))
  return SythesizedArticle
```

Implementation:
- Orchestrator concurrency + join: `app/workflows/article_creation_workflow.py:369-387`, `app/workflows/article_creation_workflow.py:392-417`
- Error handling per result: `app/workflows/article_creation_workflow.py:399-407`, overall try/except: `app/workflows/article_creation_workflow.py:427-429`
- Section Synthesizer Agent prompt + Editor tool requirement: `app/agents/section_synthesizer_agent.py:12-47`, `app/agents/section_synthesizer_agent.py:48-53`

Complexity and latency:
- Complexity: O(S) agent calls (one per section). With concurrency, wall‑time ≈ max(section_call) rather than sum.
- Latency: dominated by the slowest section + editor pass per section.

### Stitching (Final Article Composition)

High‑level: Combine synthesized sections into a single prompt (plus `source_urls` from research) and invoke the Article Synthesizer Agent to produce all final fields and `full_text_markdown`.

Pseudo‑code:
```text
function stitch_article(synthesized_article, research_notes):
  if cache.exists(final_article):
    return cache.load()

  urls = unique_urls(research_notes)
  input = { synthesized_content: synthesized_article.full_text_for_editing,
            source_urls: urls }
  result = Runner.run(article_synthesizer_agent, json(input), context=config)
  final = result.final_output_as(FinalArticle)
  cache.save(final)
  return final
```

Implementation:
- Final composition in orchestrator: `app/workflows/article_creation_workflow.py:443-468`, error handling `app/workflows/article_creation_workflow.py:477-479`
- Article Synthesizer Agent output structure and constraints: `app/agents/article_synthesizer_agent.py:40-53`, narrative/SEO rules `app/agents/article_synthesizer_agent.py:55-71`

Complexity and latency:
- Complexity: O(1) (single final agent call).
- Latency: single large‑model call; tens of seconds typical; cached runs fast.

## Heuristics and Scoring Functions

- URL extraction from research notes (dedup): `app/services/web_scraping_service.py:39-50`
- Scrapable URL filter (skip PDFs/Office docs): `app/services/web_scraping_service.py:52-80`
- Content cleaning (images/links/formatting): `app/services/web_scraping_service.py:169-188`
- Minimum content heuristics (truncate >10k words; skip too short): `app/services/web_scraping_service.py:141-152`, `app/services/web_scraping_service.py:143-146`
- Research completeness checks (missing sections): `app/workflows/article_creation_workflow.py:178-199`
- Placeholder for finding ranking: schema field only, not computed: `app/models/article_schemas.py:27-31`

Notes:
- No explicit ranking/scoring is applied to findings yet; search‑tool order is preserved.

## Python Patterns (Concurrency, Retries, Timeouts)

- Async orchestration with gather (parallel per‑section synthesis): `app/workflows/article_creation_workflow.py:392-395`
- Thread offloading for CPU/IO‑bound enhancement step (Gemini): `app/workflows/article_creation_workflow.py:495-503`
- Async HTTP with `httpx.AsyncClient` (Serper API): `app/tools/serper_websearch.py:66-71`
- Rate‑limiting with `asyncio_throttle.Throttler` (DDG): `app/tools/web_search_tool.py:11-13`, used at `app/tools/web_search_tool.py:32`
- Parallel page crawling with Crawl4AI `.arun_many(...)`: `app/services/web_scraping_service.py:120-126`
- Page timeout for crawling (30s): `app/services/web_scraping_service.py:112-117`
- Retries with cap from config (`RESEARCH_MAX_RETRIES`): `app/core/config.py:58-61`, loop in orchestrator: `app/workflows/article_creation_workflow.py:227-283`
- Multiprocessing: not used in current codebase.

## Error Handling and Fallback Trees

- Cached artifact reuse (all phases): planning `app/workflows/article_creation_workflow.py:133-137`; research `app/workflows/article_creation_workflow.py:159-163`; scraping `app/workflows/article_creation_workflow.py:315-318`; synthesis `app/workflows/article_creation_workflow.py:364-367`; final `app/workflows/article_creation_workflow.py:438-441`; gemini `app/workflows/article_creation_workflow.py:488-491`.
- Planning: try/except with user‑visible error: `app/workflows/article_creation_workflow.py:138-151`.
- Research (batch): JSON validation + failure messaging: `app/workflows/article_creation_workflow.py:201-210`.
- Research (individual):
  - Retry loop per section with configurable max: `app/workflows/article_creation_workflow.py:227-233,256-271`
  - Recovery attempt on final retry via dedicated agent: `app/workflows/article_creation_workflow.py:260-265`, recovery implementation: `app/workflows/article_creation_workflow.py:529-579`
  - On persistent failure, emit empty notes with failure summary: `app/workflows/article_creation_workflow.py:276-283`
- Scraping: Non‑fatal errors fall back to original notes: `app/workflows/article_creation_workflow.py:332-347`, `app/workflows/article_creation_workflow.py:349-351`
- Synthesis: concurrent gather wrapped in try/except; partial failures tolerated; all‑fail short‑circuit: `app/workflows/article_creation_workflow.py:392-429`
- Final article creation: guarded with try/except: `app/workflows/article_creation_workflow.py:453-479`
- Gemini enhancement: guarded with try/except; empty‑content guard: `app/workflows/article_creation_workflow.py:504-507`, `app/workflows/article_creation_workflow.py:495-527`
- Data cache load/validate with graceful fallback to recompute: `app/services/workflow_data_manager.py:39-79`

## Complexity and Latency Overview

- Planning/Outlining: O(1). Latency = single small‑model call; cached path ~0.
- Research (batch): O(1) agent call but internally proportional to number of sections and queries the agent attempts; single call latency is high and less reliable.
- Research (individual, default): O(S) agent calls; sequential per section with up to `RESEARCH_MAX_RETRIES` and optional recovery → latency ≈ sum(section latencies) + retries.
- Scraping: O(U) where U = unique URLs; Crawl4AI executes `.arun_many` with page timeout 30s; effective wall time ≈ max(page time) with internal parallelism.
- Section synthesis: O(S) agent calls in parallel; wall time ≈ max(section write + editing).
- Final article synthesis: O(1) large‑model call; tens of seconds typical.


