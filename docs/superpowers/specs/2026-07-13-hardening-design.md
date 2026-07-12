# Fantasy Political Sandbox Hardening Design

## Goal

Make scheduled simulations publish reliably, prevent unsafe state-changing HTTP calls, reject invalid LLM events before persistence, and restore a trustworthy automated test suite.

## Scope

- Retain SQLite world state and GitHub Pages publishing.
- Retain manual workflow dispatch and Groq-first/Gemini-fallback LLM behavior.
- Do not introduce external storage or OAuth in this change.

## Workflow reliability

Use one concurrency group, with cancellation disabled, for workflows that change `data/world.db` or `chronicle/`. Make `auto.yml` deploy the generated `chronicle/` artifact to GitHub Pages after committing it.

## API safety

Mutating Flask endpoints require a configured `APP_PASSWORD`; no password means reject the request. Keep read-only routes public. Limit git sync staging to `data/world.db` and `chronicle/`.

## Simulation integrity

Validate model events before persistence: participants must be distinct, known, and alive; locations must be valid; deaths must name a participant alive at that point; later events cannot reuse a newly dead character. Reject an invalid batch without partial persistence.

## Tests and documentation

Replace obsolete simulation tests with batch and validation tests, add route authorization tests, and align README and `.env.example` with Groq-primary/Gemini-fallback configuration.

## Verification

Run targeted tests and the full pytest suite.
