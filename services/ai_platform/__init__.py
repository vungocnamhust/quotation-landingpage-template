"""AI Platform Layer — thin, shared agent infrastructure (15.8 bootstrap, §1.1).

Bootstrapped by 15.8 because it is the first AI feature to ship; 15.7 (AI Service Drafter)
is the second consumer and only *adds* files here (toolset group A) — it must never modify
``runtime.py`` / ``deps.py`` / ``guardrails.py`` / ``runs.py`` / ``toolsets/catalog.py``.

Five files, no plugin system, no tool auto-discovery, no config engine:

- ``runtime.py``      — ``build_agent()``, the one factory for every ``pydantic_ai.Agent``.
- ``deps.py``          — ``CatalogReadOnlyDeps``, tenant-scoped, zero write methods.
- ``toolsets/catalog.py`` — read-only catalog lookup tools (group B: find_supplier,
  find_products, find_active_rates).
- ``guardrails.py``    — ``AllowlistRecorder`` / ``OutputValidator`` / ``RunBudget``.
- ``runs.py``          — ``AiRun`` lifecycle helpers (append-only run log).
"""
