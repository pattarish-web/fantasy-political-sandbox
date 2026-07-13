# LLM Provider Fallback Design

## Goal

Make every backend LLM call use one shared, deterministic provider sequence:
**Groq, then Gemini, then OpenAI**. The change must not alter story prompts,
simulation rules, chapter content requirements, or endpoint contracts.

## Scope

`app.llm_client.call_llm()` is the sole gateway for the simulation engine,
historian, AI character spawning, and routes that invoke those services. The
provider sequence will therefore apply consistently to every existing caller.

## Design

`call_llm()` will retain its current Groq-key loop followed by its Gemini-key
loop. When neither produces a response, it will attempt OpenAI once, using
`OPENAI_API_KEY` and `OPENAI_MODEL` (default: `gpt-5-mini`). OpenAI receives the
same prompt and JSON-only contract as the other providers. If a Pydantic model
is supplied, its JSON schema is included in the request prompt; no story prompt
is rewritten.

The terminal error is raised only after all three providers fail. Logs identify
the provider being attempted and preserve failure messages without printing
keys.

## Configuration and Deployment

- `requirements.txt` adds the official `openai` Python SDK.
- `app/config.py` exposes `get_openai_api_key()` and `OPENAI_MODEL`.
- `.github/workflows/auto.yml` passes `secrets.OPENAI_API_KEY` to both the
  simulation and historian steps.
- The GitHub secret is named exactly `OPENAI_API_KEY`; it is never committed.

## Error Handling

An absent OpenAI key skips the OpenAI attempt and leaves a clear terminal error
after Groq and Gemini are exhausted. A failed OpenAI request is logged and then
included in the same terminal failure condition. Provider failures never change
stored world state by themselves.

## Testing

Unit tests will replace provider calls with controlled failures and successes to
prove the order is Groq -> Gemini -> OpenAI and that OpenAI is not tried after a
successful earlier provider. Workflow tests will assert that both LLM-running
steps receive `OPENAI_API_KEY`.

## Non-goals

- No changes to simulation prompts, historian prompts, chapter length, or story
  logic.
- No model-routing distinction between simulation and historian in this change.
- No direct browser-to-OpenAI calls and no exposure of the API key in pages,
  exports, logs, or Git history.
