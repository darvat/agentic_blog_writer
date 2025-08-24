# Data and RAG Pipeline

## Overview

This document details data sources, ingestion and cleaning, chunking approach, retrieval strategy and freshness, plus caching policy for the agentic blog writer.

### Sources

- **Web search (APIs)**
  - Serper (Google Search API) via async HTTP client.
    - Evidence:
```41:95:app/tools/serper_websearch.py
@function_tool
async def perform_serper_web_search(
    query: str,
    location: Optional[str] = None,
    gl: Optional[str] = None,
    hl: Optional[str] = None,
    tbs: Optional[str] = None,
    num_results: Optional[int] = None,
) -> List[Dict[str, str]]:
    # Assign default values if arguments are None
    loc = location if location is not None else "United States"
    g_lang = gl if gl is not None else "us"
    h_lang = hl if hl is not None else "en"
    time_based_search = tbs if tbs is not None else "qdr:y"
    num = num_results if num_results is not None else 3

    url = "https://google.serper.dev/search"
    payload = json.dumps({
        "q": query,
        "location": loc,
        "gl": g_lang,
        "hl": h_lang,
        "tbs": time_based_search,
        "num": num
    })
```
  - Bing Web Search.
    - Evidence:
```29:58:app/tools/bing_websearch.py
actual_max_results = max_results if max_results is not None else 3
subscription_key = os.getenv('BING_SEARCH_V7_SUBSCRIPTION_KEY')
endpoint = os.getenv('BING_SEARCH_V7_ENDPOINT') + "v7.0/search"
params = {
    'q': query,
    'mkt': mkt if mkt else 'en-US',
    'count': actual_max_results
}
# search in last 365 days
today = datetime.now().date()
past_date = today - timedelta(days=365)
params['freshness'] = f"{past_date.strftime('%Y-%m-%d')}..{today.strftime('%Y-%m-%d')}"
```
  - DuckDuckGo (library-based, no API key).
    - Evidence:
```32:40:app/tools/web_search_tool.py
async with throttler:
    actual_max_results = max_results if max_results is not None else 5
    with DDGS() as ddgs:
        results = list(ddgs.text(query, max_results=actual_max_results, timelimit="y", region=os.getenv("DDG_REGION")))
```

- **Web crawling/scraping**
  - Crawl4AI async crawler for article pages; markdown extraction and cleaning.
    - Evidence:
```92:167:app/services/web_scraping_service.py
scrapable_urls = self._filter_scrapable_urls(urls)
browser_config = BrowserConfig(headless=True, verbose=False)
crawler_config = CrawlerRunConfig(exclude_external_images=True, exclude_external_links=True, verbose=False, page_timeout=30000)
async with AsyncWebCrawler(config=browser_config) as crawler:
    crawl_results: List[CrawlResult] = await crawler.arun_many(urls=scrapable_urls, config=crawler_config)
... # pick fit_markdown/raw_markdown, truncate to 10000 words, clean
```
  - Firecrawl and Newspaper4k alternatives.
    - Evidence:
```12:33:app/tools/scraper.py
response = firecrawl.scrape_url(url, formats=["markdown"], only_main_content=True)
cleaned_markdown = re.sub(r'!?\[(.*?)\]\(.*?\)', r'\1', response.markdown)
```
```51:57:app/tools/scraper.py
article = Article(url)
article.download()
article.parse()
return article.text
```

- **Files**
  - Workflow artifacts cached under `data/` per title/phase (JSON).
    - Evidence:
```22:37:app/services/workflow_data_manager.py
file_path = phase_dir / f"{phase}.json"
with open(file_path, "w") as f:
    if hasattr(data, 'model_dump_json') and callable(data.model_dump_json):
        f.write(data.model_dump_json(indent=2))
    elif isinstance(data, (dict, list)):
        json.dump(data, f, indent=2)
```

### Licensing and Compliance Notes

- Respect third‑party site ToS/robots; Crawl4AI uses a headless browser; restricts external assets and sets per‑page timeout.
- APIS: Serper and Bing require API keys; usage bound by respective ToS. DuckDuckGo library has rate‑limit via throttler.
- PDF/Office docs are excluded from scraping by default, avoiding specialized parsing and potential licensing ambiguity.
  - Evidence:
```60:77:app/services/web_scraping_service.py
if (url_lower.endswith('.pdf') or url_lower.endswith('.doc') or url_lower.endswith('.docx') or ...):
    excluded_urls.append(url)
```

### Ingestion and Cleaning

Pipeline phases orchestrated by `ArticleCreationWorkflow`: plan → research (search APIs) → scrape URLs → synthesize → finalize → Gemini enhance.
- Evidence:
```77:90:app/workflows/article_creation_workflow.py
self.display_manager.display_phase_start(3, "Web Content Scraping")
final_research_notes = await self._scrape_web_content(research_notes)
```
```320:347:app/workflows/article_creation_workflow.py
urls_to_scrape = self.web_scraping_service._extract_urls_from_research(original_research_notes)
notes_to_augment = await self.web_scraping_service.extract_and_scrape_urls(original_research_notes)
```

Cleaning steps on scraped markdown:
- Remove images and HTML img tags, remove raw URL parentheses, collapse multiple newlines, trim.
  - Evidence:
```169:188:app/services/web_scraping_service.py
content = re.sub(r"!\[.*?\]\(.*?\)", "", content)
content = re.sub(r"<img .*?>", "", content)
content = re.sub(r"\(http[^)]*\)", "()", content)
content = re.sub(r"\[\s*\]\(\)", "", content)
content = re.sub(r"\n{2,}", "\n", content)
return content.strip()
```

### Chunking

There is no vector‑store RAG chunking implemented in code at present. Scraped content is truncated to a maximum of 10,000 words per URL and stored inline per finding.
- Evidence:
```141:147:app/services/web_scraping_service.py
words = content.split()
if len(words) > 10000:
    content = " ".join(words[:10000])
```

Recommended chunking strategy (for future RAG):
- **Chunker**: token‑aware fixed windows.
- **Chunk size (tokens)**: 800 (default). Justification: balances retrieval granularity vs. context usefulness for synthesis.
- **Overlap (tokens)**: 120. Justification: preserves context across boundaries.
- **Splitter**: paragraph/sentence boundaries first, fallback to token windows.

Parameter table:

| Parameter | Default | Justification |
|---|---:|---|
| chunk_size_tokens | 800 | Good balance of context vs. retrieval noise |
| chunk_overlap_tokens | 120 | Minimizes boundary loss without high duplication |
| max_chunks_per_doc | 500 | Prevents runaway memory/latency on very long pages |
| truncate_long_docs_tokens | 120000 | Safety limit; today we truncate at words=10k |

Note: Implementers should update this doc with evidence links if/when a chunker is added.

### Retrieval Strategy

Current system does not perform vector retrieval over an index. Retrieval is prompt‑time: sections are synthesized using research notes and optional scraped content, passed directly to the LLM agents.
- Evidence (no embedding/vector search present; only search APIs + scraping + direct synthesis inputs): repo has no `faiss`, `chroma`, `pinecone`, or embedding calls. `rank-bm25` and `tiktoken` are present in dependencies but unused in code.

If adding RAG later:
- **Index**: local FAISS or SQLite‑vector; alternative: managed store.
- **Retriever**: hybrid (sparse BM25 + dense cosine), top‑k=6, MMR lambda=0.2.
- Update this section with code evidence on introduction.

### Freshness Policy

- Search freshness:
  - Serper: default `tbs=qdr:y` (past year).
    - Evidence: see Serper defaults above.
  - Bing: explicit date‑range of last 365 days.
    - Evidence: see Bing `freshness` above.
  - DuckDuckGo: `timelimit="y"` (past year).
    - Evidence: see DDG usage above.

- Scrape caching freshness: cached per title/phase; no TTL, manual invalidation supported.
  - Evidence:
```81:85:app/services/workflow_data_manager.py
def has_cached_data(self, title_slug: str, phase: str) -> bool:
    file_path = self.data_dir / title_slug / f"{phase}.json"
    return file_path.exists()
```

### Caching Policy

- Levels
  - **Phase cache (file cache)**: JSON files per `title_slug/phase`. Used across planning, researching, scraping, synthesis, final article, and Gemini enhancement.
    - Evidence:
```132:146:app/workflows/article_creation_workflow.py
loaded_data = self.data_manager.load_data(self.title_slug, phase_name, SectionPlans)
if loaded_data:
    self.printer.update_item(phase_name, "\ud83d\udcc1 Using cached article plan", is_done=True)
    return loaded_data
```
```315:341:app/workflows/article_creation_workflow.py
loaded_data = self.data_manager.load_data(self.title_slug, phase_name, ResearchNotes)
... save_data(...)
```
  - No prompt/result memoization beyond these phase artifacts.

- Invalidation
  - Manual: remove specific phase file or call clear method.
    - Evidence:
```86:101:app/services/workflow_data_manager.py
def clear_cache(self, title_slug: str, phase: str | None = None) -> None:
    if phase:
        file_path = phase_dir / f"{phase}.json"
        if file_path.exists():
            file_path.unlink()
    else:
        for file_path in phase_dir.glob("*.json"):
            file_path.unlink()
        if not any(phase_dir.iterdir()):
            phase_dir.rmdir()
```

- TTL
  - None configured. Rationale: workflows are typically single‑run per article; deterministic re‑runs prefer explicit regeneration.

Parameter table (Caching):

| Parameter | Default | Justification |
|---|---:|---|
| cache_backend | file | Simple, inspectable JSON artifacts per phase |
| use_cache_planning | true | Avoids recomputing section plan |
| use_cache_research | true | Preserves gathered URLs/results |
| use_cache_scrape | true | Avoids re‑scraping remote sites |
| use_cache_synthesis | true | Saves cost/time on LLM synthesis |
| use_cache_final | true | Reuses final article if unchanged |
| use_cache_gemini | true | Reuses enhanced article if unchanged |
| ttl_seconds | null | Not implemented; manual invalidation only |

### Configuration

Central configuration via `app/core/config.py` and environment variables.
- Evidence:
```39:69:app/core/config.py
class Config:
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY")
    RESEARCH_STRATEGY: str = os.getenv("RESEARCH_STRATEGY", "individual")
    RESEARCH_MAX_RETRIES: int = int(os.getenv("RESEARCH_MAX_RETRIES", "2"))
    def validate_config(cls) -> bool:
        required_keys = ["OPENAI_API_KEY", "GEMINI_API_KEY"]
```

Parameter table (Research):

| Parameter | Default | Justification |
|---|---:|---|
| RESEARCH_STRATEGY | individual | More reliable per‑section runs vs. batch |
| RESEARCH_MAX_RETRIES | 2 | Allows recovery without long loops |
| SERPER.num_results | 3 | Small, high‑precision organic set |
| SERPER.tbs | qdr:y | Prioritize recent content |
| DDG.max_results | 5 | Balanced breadth for library search |
| BING.count | 3 | Cost/latency control with freshness window |

### Notes on RAG Scope

The current system is “search + scrape + synthesize,” not vector‑indexed RAG. If RAG is added later, update this doc with:
- Embedding model and dims.
- Index type and storage.
- Chunking/tokenization specifics with evidence links.
- Retriever params (top‑k/MMR/filters) and freshness design.


