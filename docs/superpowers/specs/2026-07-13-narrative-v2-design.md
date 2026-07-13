# Narrative V2 Design

## Goal

Make the Thai fantasy-political chronicle read as a coherent novel: each
published chapter follows one causal conflict, preserves canon, gives its
politics concrete consequences, and never falls behind the simulated world.

## Scope and Decisions

- Preserve `data/world.db` as the authority for current character status,
  relationships, artifacts, and wars. Do not reset the world.
- Treat the contradictory published opening as legacy presentation, not as
  immutable canon. Replace the reader-facing opening with a consistent,
  professionally edited canonical retelling that honors the database facts.
- A character cannot be resurrected by default. The simulation schema and
  validation will reject resurrection until a separately designed revival
  system exists.
- The automatic workflow will simulate exactly three events before drafting
  one chapter. It therefore cannot accumulate an event backlog.

## Architecture

### Canon and world bible

`story_state` becomes a structured narrative snapshot. In addition to deaths,
wars, resolved events, and open threads, it retains character changes,
relationship changes, artifact ownership, and a compact faction ledger. A
new versioned `world_bible` record stores the setting rules, political
institutions, technology level, and each faction's objective, leverage, and
current pressure. The Historian receives a focused excerpt rather than raw
unbounded history.

### Plan, prose, and critique pipeline

For one three-event bundle the Historian first asks the model for a validated
`ChapterPlan`. The plan names the at-most-two present-time POV characters,
central conflict, political stake, meaningful choice, cost, final unresolved
thread, and source rounds. Only a valid plan is sent to the prose prompt.

The generated `ChapterResult` is checked deterministically for non-empty
title/body, allowed tone, Thai-length bounds, dead-character present action,
reused dialogue, and plan/source-round agreement. A separate structured
critic scores continuity, causality, political clarity, character voice, and
repetition. If it identifies a blocking defect, the Historian rewrites once
with the critique; a second failure returns an error without publishing.

### Event facts

Every simulation encounter persists a typed `story_facts` payload. The
payload records death, power, relationship, artifact, war, and explicit
thread information. Validation rejects unknown participants, duplicate deaths,
nonparticipant deaths, and all resurrection fields. Advancing a chapter
updates the canonical state atomically with the chapter row.

### Published opening

A migration/export routine builds a small, consistent opening sequence from
the current canonical database facts. It replaces the duplicate and
contradictory chapter pages, keeps all source text recoverable in Git, and
rebuilds the index. The narrative uses a fixed Thai register and explicitly
defines this world as magitech, making recordings and communication technology
consistent with its fantasy setting.

## Failure Handling

- Invalid plans, prose, or critique responses do not consume events or update
  canon.
- A failed rewrite does not publish a partial chapter.
- A corrupt persisted story state is normalized and reconstructed from the
  relational world tables where possible.

## Verification

Tests cover plan validation, persistence of every fact type, rejection of
resurrection, one-pass critique/rewrite, length/tone validation, event queue
parity, canon continuity, and regenerated chronicle output. The full suite
must pass before merge. GitHub Actions then publishes the changed `chronicle/`
directory to Pages.
