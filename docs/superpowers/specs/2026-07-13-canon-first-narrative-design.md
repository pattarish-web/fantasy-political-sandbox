# Canon-First Narrative Pipeline Design

## Goal

Generate Thai fantasy-political chapters that advance the world state without
replaying resolved events, reviving dead characters in the present timeline,
or treating a large batch of unrelated events as one chapter.

## Scope

This change improves story quality and continuity only. It does not redesign
the GitHub Actions dashboard, authentication, or the simulation's broader
economy and faction model.

## Architecture

### Canon ledger

Add a `story_state` table containing one JSON document. It is the authoritative
summary of facts resolved by generated chapters:

- `deaths`: character names whose deaths are established in published prose.
- `regime_changes`: completed changes of political leadership.
- `wars`: declared conflicts already established in prose.
- `resolved_events`: normalized event signatures already narrated.
- `open_threads`: unresolved consequences that a later chapter may advance.

The historian reads this state before composing a chapter. After it accepts a
chapter, it derives a replacement state from the selected logs and saves it in
the same transaction as the chapter record.

### Chapter-sized event selection

The historian selects at most three undrafted events per chapter. It never
mixes an event batch into the "prior world" context. The next invocation picks
the following events, leaving the rest undrafted.

### Narrative contract

The historian receives a compact canon ledger, a short prior-chapter synopsis,
and only the selected source events. The prompt requires a Thai chapter with:

- one central conflict;
- no more than two present-time POV characters;
- a concrete choice and cost for the main character;
- at most one newly established death;
- no recap of resolved events except a clearly marked brief memory;
- no reused dialogue from the supplied prior chapter.

The result remains JSON (`title`, `body`, `tone`) so it fits the existing export
pipeline.

### Validation boundaries

The simulation validates LLM encounters before persisting them: both
participants must be distinct, alive known characters; any declared death must
be a participating alive character. Invalid batches fail atomically before
writing any logs.

The historian rejects output that mentions a canon-dead character in
present-time narrative unless that character is explicitly one of the selected
new deaths. Detection is deliberately conservative and tests use direct Thai
name mentions; it prevents the observed regression without attempting to
understand every literary tense.

## Data flow

1. Simulation validates and persists a batch of world events.
2. Historian selects the next one to three undrafted events.
3. Historian loads the canon ledger and a bounded summary of the prior chapter.
4. LLM writes one chapter under the narrative contract.
5. Historian validates the draft against canon, saves it, updates canon, and
   exports static pages.

## Error handling

- Invalid simulation batches return an error before mutation.
- An invalid historian draft returns an error and leaves logs undrafted, so it
  can be retried after the prompt or provider is corrected.
- Missing story state is treated as an empty state, preserving existing worlds.

## Tests

- DB state defaults, persistence, and update behavior.
- Historian takes no more than three events and does not echo them as prior
  context.
- Historian prompt includes canon and rejects a canonical death repeated in a
  new present-time chapter.
- Simulation refuses unknown, dead, self-paired, and non-participant death
  encounters without saving partial state.

## Success criteria

Published chapter N+1 receives only selected new events plus canonical facts;
it cannot re-establish an earlier death, and an invalid simulation response
cannot corrupt the world database.
