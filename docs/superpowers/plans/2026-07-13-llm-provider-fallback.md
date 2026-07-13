# LLM Provider Fallback Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every backend LLM call fall back from Groq to Gemini to OpenAI.

**Architecture:** `call_llm()` stays the single gateway used by simulation, historian, spawn, and routes. It gains one OpenAI adapter and configuration accessor; all callers retain their prompts and contracts.

**Tech Stack:** Python 3.11, Pydantic, Groq SDK, Google Generative AI SDK, OpenAI Python SDK, pytest, GitHub Actions.

## Global Constraints

- Provider order is exactly Groq -> Gemini -> OpenAI.
- Do not change simulation prompts, historian prompts, chapter length, story logic, route contracts, or exports.
- Use GitHub secret `OPENAI_API_KEY`; never commit or log a key.
- Default OpenAI model: `gpt-5-mini`, overridden with `OPENAI_MODEL`.

---

### Task 1: OpenAI configuration

**Files:** Modify `requirements.txt`, `app/config.py`, `tests/test_config.py`.

**Produces:** `config.OPENAI_MODEL: str` and `config.get_openai_api_key() -> str`.

- [ ] **Step 1: Write the failing test**

```python
def test_get_openai_api_key_strips_whitespace(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "  test-openai-key  ")
    assert config.get_openai_api_key() == "test-openai-key"
```

- [ ] **Step 2: Verify red**

Run: `python -m pytest tests/test_config.py -q`

Expected: FAIL because `get_openai_api_key` does not exist.

- [ ] **Step 3: Implement minimal configuration**

```python
# requirements.txt
openai>=1.0

# app/config.py
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-5-mini").strip() or "gpt-5-mini"

def get_openai_api_key() -> str:
    return os.environ.get("OPENAI_API_KEY", "").strip()
```

- [ ] **Step 4: Verify green and commit**

Run: `python -m pytest tests/test_config.py -q`

Expected: PASS.

Commit: `git add requirements.txt app/config.py tests/test_config.py; git commit -m "feat: add OpenAI provider configuration"`

### Task 2: Ordered OpenAI fallback

**Files:** Modify `app/llm_client.py`; create `tests/test_llm_client.py`.

**Produces:** `_call_openai(prompt, key, response_schema) -> str`; `call_llm()` returns the first successful provider response.

- [ ] **Step 1: Write the failing order test**

```python
def test_call_llm_uses_openai_after_groq_and_gemini_fail(monkeypatch):
    monkeypatch.setattr(llm_client.config, "get_api_keys", lambda: ["groq"])
    monkeypatch.setattr(llm_client.config, "get_gemini_api_keys", lambda: ["gemini"])
    monkeypatch.setattr(llm_client.config, "get_openai_api_key", lambda: "openai")
    monkeypatch.setattr(llm_client, "_call_groq", lambda *args: (_ for _ in ()).throw(RuntimeError()))
    monkeypatch.setattr(llm_client, "_call_gemini", lambda *args: (_ for _ in ()).throw(RuntimeError()))
    monkeypatch.setattr(llm_client, "_call_openai", lambda *args: '{"ok": true}')
    assert llm_client.call_llm("prompt") == '{"ok": true}'
```

- [ ] **Step 2: Verify red**

Run: `python -m pytest tests/test_llm_client.py -q`

Expected: FAIL because `_call_openai` does not exist or is never reached.

- [ ] **Step 3: Implement adapter and final fallback**

```python
def _call_openai(prompt, key, response_schema=None):
    messages = [{"role": "system", "content": "You are a helpful assistant. Output ONLY valid JSON."}]
    if response_schema:
        messages[0]["content"] += " Match this JSON Schema:\n" + json.dumps(response_schema.model_json_schema())
    messages.append({"role": "user", "content": prompt})
    response = OpenAI(api_key=key).chat.completions.create(
        model=config.OPENAI_MODEL, messages=messages,
        response_format={"type": "json_object"}, temperature=0.7, max_tokens=8000,
    )
    return response.choices[0].message.content
```

After the Gemini loop, only call this adapter when `config.get_openai_api_key()` is non-empty. Log attempts and errors without the key; include OpenAI in the terminal error.

- [ ] **Step 4: Add short-circuit test and verify green**

```python
def test_call_llm_does_not_try_openai_after_groq_success(monkeypatch):
    monkeypatch.setattr(llm_client.config, "get_api_keys", lambda: ["groq"])
    monkeypatch.setattr(llm_client.config, "get_gemini_api_keys", lambda: [])
    monkeypatch.setattr(llm_client.config, "get_openai_api_key", lambda: "openai")
    monkeypatch.setattr(llm_client, "_call_groq", lambda *args: '{"source": "groq"}')
    monkeypatch.setattr(llm_client, "_call_openai", lambda *args: pytest.fail("must not run"))
    assert llm_client.call_llm("prompt") == '{"source": "groq"}'
```

Run: `python -m pytest tests/test_llm_client.py -q`

Expected: PASS.

Commit: `git add app/llm_client.py tests/test_llm_client.py; git commit -m "feat: add OpenAI LLM fallback"`

### Task 3: Workflow secret propagation

**Files:** Modify `.github/workflows/auto.yml`, `.github/workflows/simulate.yml`, `.github/workflows/historian.yml`, `tests/test_workflows.py`.

- [ ] **Step 1: Write a failing assertion**

```python
for workflow in (auto, historian, simulate):
    assert "OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}" in workflow
```

- [ ] **Step 2: Verify red**

Run: `python -m pytest tests/test_workflows.py -q`

Expected: FAIL because the secret is absent.

- [ ] **Step 3: Add the secret to every LLM Python step**

```yaml
env:
  OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
```

This appears beside the existing Groq and Gemini variables in both `auto.yml` steps, the simulation step, and the historian step.

- [ ] **Step 4: Verify and commit**

Run: `python -m pytest tests/test_workflows.py -q && python -m pytest -q`

Expected: all tests PASS.

Commit: `git add .github/workflows tests/test_workflows.py; git commit -m "ci: provide OpenAI fallback secret"`

### Task 4: Final verification

- [ ] **Step 1: Verify diff hygiene**

Run: `git diff --check && git status --short`

Expected: no whitespace errors and no uncommitted implementation changes.

- [ ] **Step 2: Verify the provider boundary**

Run: `rg -n "call_llm\(|_call_openai|OPENAI_API_KEY" app .github/workflows tests`

Expected: OpenAI appears only in shared provider/configuration/workflow code; narrative prompt text is unchanged.

- [ ] **Step 3: Push verified commits**

Run: `git push origin master`

Expected: remote `master` advances with the fallback implementation.
