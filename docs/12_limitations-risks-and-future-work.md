# Limitations, Risks, and Future Work

## Overview

This document summarizes the system’s current limitations, enumerates legal/ethical/operational risks, and proposes a pragmatic roadmap with explicit acceptance criteria. The focus is on the end‑to‑end pipeline documented in `docs/02_system-architecture.md` and the prompting and safety guardrails described in `docs/05_prompting-strategy-and-templates.md`.

### Known limitations

- **Accuracy and factuality**
  - LLM outputs may contain hallucinations or misinterpretations, especially when inputs are noisy (web results, partial scrapes) or claims are time‑sensitive.
  - The Gemini enhancement stage performs search‑grounded fact checks, but verification is opportunistic rather than exhaustive; important claims may remain unverified.
  - References are listed at the end; there is no per‑claim inline citation or automated provenance tracking within paragraphs.

- **Coverage and retrieval completeness**
  - Research queries per section are limited (max ~3 results per query by design); relevant sources beyond the first page or outside the chosen engines may be missed.
  - Paywalled, dynamic, or bot‑protected sites can block scraping, reducing source diversity and depth.
  - Multilingual topics and locale‑specific results are only partially supported; coverage may skew toward English and highly indexed domains.

- **Brittleness and reliability**
  - The pipeline depends on multiple external APIs (OpenAI Agents SDK, Serper/Bing/DDG, Crawl4AI/Firecrawl, Gemini). Rate limits, outages, or API changes can fail runs.
  - Strict JSON schemas in intermediate agents improve discipline but increase failure sensitivity to minor formatting drift.
  - Non‑determinism across model versions and prompts can lead to run‑to‑run variability, complicating debugging and reproducibility.

- **Secondary limitations (pragmatic constraints)**
  - Latency and cost scale with the number of sections and sources; budget management is manual.
  - Evaluation is mostly qualitative; there are no automated factuality or coverage scores, and limited regression tests on curated topics.
  - Security and privacy safeguards are basic (environment variables, minimal input sanitation); there is no PII scanning or content redaction.

### Risks

- **Legal**
  - Copyright: quoting or paraphrasing scraped content may exceed fair use without robust attribution/transformative use analysis.
  - Terms of service/robots: automated access to sites may violate publisher policies; retention of scraped artifacts in `data/` may be non‑compliant.
  - Data protection: accidental inclusion of personal data (PII) from web pages could trigger GDPR/CCPA obligations; no DSR/retention processes exist.

- **Ethical**
  - Misinformation amplification: hallucinated or outdated claims may be presented confidently, potentially misleading readers.
  - Bias and framing: search rankings and training data biases can shape coverage and tone; no systematic bias audit is in place.
  - Transparency: outputs are not consistently labeled as AI‑assisted; editorial boundaries between synthesis and original research are not explicit.

- **Operational**
  - Reliability: chained dependencies magnify failure modes (timeouts, schema mismatches, insufficient retries/backoff).
  - Cost control: bursty usage can incur steep API bills; there is no hard budget enforcement or alerting.
  - Secrets and access: API keys are environment‑based without fine‑grained rotation or automated scanning for accidental leakage.

### Roadmap

#### Near term (0–4 weeks)

- **Introduce per‑claim citation scaffolding (optional inline anchors tied to sources)**
  - Acceptance criteria:
    - For ≥80% of factual sentences containing numbers/dates/entities, the system attaches a machine‑readable citation anchor (e.g., [1], [2]) mapped to a reference URL.
    - No JSON schema regressions; final markdown renders without broken anchors on a 10‑article smoke suite.

- **Harden retrieval and scraping (multi‑engine fan‑out, graceful degradation)**
  - Acceptance criteria:
    - Parallelize research across at least two engines (Serper + DDG or Bing) with deduplication; unique source count increases by ≥30% on the smoke suite.
    - Scraper fallback order implemented; ≥90% of URLs produce non‑empty cleaned content across the suite.

- **Adversarial input sanitation and prompt‑injection defenses**
  - Acceptance criteria:
    - Strip HTML/script tags from inputs passed to agents; escape/neutralize instructions embedded in scraped content.
    - Zero recorded “format‑switch” failures (e.g., non‑JSON where JSON required) on 50 randomized runs.

- **Basic observability and budget controls**
  - Acceptance criteria:
    - Per‑phase metrics: latency, token usage, cost estimates logged and summarized per run.
    - Configurable hard cap aborts a run when projected cost exceeds threshold; alert/log message emitted.

#### Mid term (1–3 months)

- **Inline provenance and reference deduplication at paragraph level**
  - Acceptance criteria:
    - Each paragraph with factual claims contains at least one resolvable citation; duplicate URLs collapsed; references include 1–2 sentence relevance notes.
    - Automated checker verifies ≥95% anchor→URL integrity on the suite.

- **Evaluation harness (factuality, coverage, readability)**
  - Acceptance criteria:
    - Curated test set (≥30 topics) with answer keys; automated scoring pipelines produce per‑release dashboards.
    - Regression gate blocks merges if factuality or coverage scores drop by >5% relative to baseline.

- **Policy and safety layer (PII scan, content filters, disclaimers)**
  - Acceptance criteria:
    - PII detector flags/blocks drafts containing emails/phone numbers/IDs with ≤2% false positives on the suite.
    - All outputs include a configurable disclosure and references section; refusal/clarification templates integrated for policy violations.

- **Schema/versioning and cache hygiene**
  - Acceptance criteria:
    - Versioned intermediate schemas with migration helpers; old caches auto‑invalidated when schema changes.
    - Zero “key error/field missing” crashes across 100 randomized runs.

#### Long term (3–6+ months)

- **Curated knowledge base + RAG to reduce dependence on ad‑hoc web search**
  - Acceptance criteria:
    - Indexed corpus with freshness policy; retrieval benchmarks show ≥20% factuality lift vs. search‑only baseline.
    - Cost per article decreases by ≥25% at equal or better measured coverage.

- **Human‑in‑the‑loop editorial workflow**
  - Acceptance criteria:
    - Reviewer UI/CLI supports claim pinning, source substitution, and targeted re‑generation; average review time per article <30 minutes on pilot.
    - Audit log of edits and rationale stored with the final artifact.

- **Reliability engineering (SLOs, retries, circuit breakers)**
  - Acceptance criteria:
    - 99th percentile end‑to‑end latency SLO defined and met on weekly runs; failure rate <3% with automatic retry/backoff and circuit breaking for flapping APIs.
    - Cost anomaly detection alerts on >2× baseline spend within 24 hours.

- **Security and compliance maturation**
  - Acceptance criteria:
    - Secrets rotated automatically; key scopes minimized; periodic leak scans pass.
    - Data retention policy enforced for cached artifacts; documented process for DSRs (export/delete upon request).

---

The above roadmap balances immediate hardening (robustness, observability, defenses) with medium‑term evaluation and provenance, and longer‑term shifts toward curated retrieval and editorial controls. Acceptance criteria are deliberately measurable to enable automated gating and continuous quality tracking.


