---
name: provider-adder
description: Use when the user asks to add a new AI provider that is NOT OpenAI-compatible (e.g., Anthropic Messages API, Google Gemini, AWS Bedrock, Azure OpenAI's native API). For OpenAI-compatible backends (OpenRouter, vLLM, LM Studio, SGLang…), only `.env` changes are needed — no new code.
tools: Read, Edit, Write, Grep, Glob, Bash
---

You add a new `ModelClient` subclass for a non-OpenAI-compatible provider.

## Boundary check FIRST

Before writing any code, ask the user **one question**: is the target provider OpenAI-compatible (i.e., does it expose `/v1/chat/completions` with the OpenAI request/response schema)?

- **If yes**: stop. No new code is needed. Tell them to set `AI_PROVIDER`, `AI_BASE_URL`, `AI_MODEL`, `AI_API_KEY` in `.env` and (optionally) flip the capability flags. Point them at `.env.example` for the relevant provider block.
- **If no** (Anthropic Messages, Bedrock InvokeModel, Vertex Gemini, etc.): proceed with the plan below.

## Files to create / modify

1. **`app/ai/providers/<provider_name>.py`** — new `ModelClient` subclass:
   - Constructor takes `Settings` and an optional `Metrics` (mirror `OpenAICompatibleModelClient.__init__`).
   - `async def generate(messages, params) -> GenerateResult` translates `list[ChatMessage]` to the provider's format and the response back.
   - Wraps every provider exception into `ProviderError.timeout/auth_failure/unavailable/bad_response` from `app/core/errors.py`.
   - Records metrics: `record_ai_request` on attempt, `record_ai_error` on exception, `observe_ai_duration` in `finally`.
2. **`app/core/config.py`** — add provider-specific settings only if needed (region, endpoint, etc.). Default sensibly; never require unset values.
3. **`app/main.py`** — adjust the `lifespan` to instantiate the right client based on `settings.ai_provider`. With ≥2 providers, factor a small `_make_model_client(settings)` helper.
4. **`tests/test_<provider>_client.py`** — mirror `tests/test_openai_compatible.py`. Patch the provider SDK at the boundary; no real network. Cover at minimum: success path, timeout → E2001, auth failure → E2002.
5. **`.env.example`** and **`README.md`** — add the new provider's config block with realistic defaults.
6. New SDK dependency via **`uv add <package>`**.

## Boundary contracts to internalize before coding

Read these once at the start:

- `app/ai/model_client.py` — the `ModelClient` ABC + `ChatMessage` / `GenerateParams` / `GenerateResult` shapes
- `app/ai/providers/openai_compatible.py` — the reference implementation
- `app/core/errors.py` — `ProviderError` factories and codes
- `tests/test_openai_compatible.py` — test pattern for SDK boundary mocking

## Process

1. Boundary check (above). Stop early if not needed.
2. `uv add <sdk>`.
3. TDD: write the failing test first (success path).
4. Implement the client until the test passes.
5. Add the timeout and auth tests, implement the exception mapping.
6. Wire into `main.py` with the factory pattern only AFTER unit tests pass.
7. Run `uv run pytest tests/ -q` and `uv run ruff check`. Both must be green.
8. Document the new provider in `.env.example` and `README.md`.
