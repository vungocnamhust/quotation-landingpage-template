---
name: quotation-ai-content-agent
description: Govern the LLM content-generation layer of this repo. Use when changing prompts under prompts/v1/**, content budgets, services/section_content_generator.py, llm_client.py, quotation_agent.py, image_selector.py, or any typed AI draft output. Enforces the versioned-prompt SSOT, typed-and-validated output models, budget-derived length limits, fail-closed drafting, and the prompt/budget sync between backend and frontend.
---

# Quotation AI Content Agent Governor

The AI layer here is deliberately simple: one provider-agnostic model factory,
`pydantic-ai` `Agent` calls with **typed output models**, and prompts stored as
versioned YAML. Keep it that way — do not introduce a framework, a chain, a
vector store, or an autonomous tool loop without an explicit request.

## Architecture (read before editing)

```
prompts/v1/*.yaml  →  prompts/loader.py (PromptLoader → PromptBundle)
                              ↓
core/rules/content_budgets.py (min/max chars registry)
                              ↓
services/section_content_generator.py  (typed _CopyModel outputs + pydantic_ai.Agent)
                              ↓
llm_client.get_model()  →  OpenAIChatModel over an OpenAI-compatible provider
```

- `llm_client.get_model()` is the **only** place a model/provider is constructed.
  It reads `DEEPSEEK_API_KEY` / `DEEPSEEK_API_BASE` / `DEEPSEEK_MODEL` and falls
  back to `OPENAI_API_KEY`. Never instantiate a provider or hardcode a model name
  elsewhere; never read the API key outside this module.
- Prompt text is data, not code. Sections live in `prompts/v1/sections/*.yaml`,
  modes in `prompts/v1/modes/`, brand voice in `prompts/v1/brands/`, plus
  `system_base.yaml`, `ground_rules.yaml`, `prompt_recipes.yaml`,
  `content_budgets.yaml`. Never inline a prompt string in a service.
- Adding a prompt version means a new `prompts/vN/` directory — never mutate `v1`
  semantics in place once drafts reference it.

## Rules

1. **Typed output only.** Every generation defines a `_CopyModel` subclass
   (`extra="forbid"`, whitespace-collapsing + HTML-rejecting validators) and passes
   it as the agent's output type. No free-text completion, no manual `json.loads`
   of model output.
2. **Lengths come from budgets.** `min_length`/`max_length` derive from
   `get_content_budget_registry("v1")` (`get_spec` / `get_max_chars` with an explicit
   fallback). Never hardcode a character limit in an output model.
3. **Budgets are shared with the frontend.** After editing
   `prompts/v1/content_budgets.yaml`, regenerate
   `quote-generator/config/contentBudgets.json`:
   ```bash
   cd quote-generator && npm run sync:budgets
   ```
   and run `PYTHONPATH=. pytest tests/test_content_budgets.py`.
4. **Fail closed.** Invalid or missing candidates raise `ContentGenerationError`
   and persist nothing. Never fall back to a silent default, a truncated string,
   or a partially-valid draft.
5. **Facts in, copy out.** Prompts receive a `facts_snapshot`; the model never
   invents prices, dates, hotel names, or itinerary structure. Structural data
   comes from the reconcilers/services — the LLM only writes prose.
6. **Bundle transparency.** Keep `build_prompt_bundle()` returning the exact
   system/user prompt sent, so Content Studio can display it. Do not add hidden
   prompt mutation after bundle construction.
7. **Batch endpoints stay scope-limited.** `generate`,
   `generate_narrative_batch`, and `generate_itinerary_days_batch` are separate on
   purpose (different output shapes and budgets). Add a new scope via
   `services/content_registry.py` + a section YAML, not by widening an existing one.
8. **Async boundary.** Generation methods are `async` because the agent call is
   real async I/O. Keep prompt assembly and validation synchronous and pure.
9. **No secrets, no logs of raw keys.** Prompt bundles and errors may be surfaced
   to staff UI — keep credentials and internal URLs out of them.

## Post-Edit Gate

```bash
PYTHONPATH=. pytest tests/test_prompt_loader.py tests/test_content_budgets.py \
  tests/test_content_generation_instruction.py \
  tests/test_content_generation_with_request_brief.py
```

Add a case to those suites for any new scope, mode, or budget key. Do not call a
prompt change done on a manual eyeball of one generated draft.
