# Protected World Reset Design

## Goal

Prevent accidental deletion of the world narrative while preserving a reliable,
owner-only reset and restore path.

## Public and Dashboard UI

Remove all reset controls and reset JavaScript from exported public chronicles
and the local mobile dashboard. A public page must never contain a GitHub token
reset path, a reset password, or a destructive action button.

## Protected Reset

The `Reset world and republish` GitHub Actions workflow remains the only reset
entry point. Manual dispatch requires an input named `confirmation` whose exact
value must be `RESET WORLD`. A guard step fails before any mutation when the
input differs.

Immediately before resetting, the workflow creates and pushes an annotated tag
named `world-backup-<UTC timestamp>` at the current commit. The tag is the
backup: it contains the prior `data/world.db`, `chronicle/`, and tracked
`story_summary.json` without duplicating those files in the repository.

## Restore

Add `Restore world backup` as a manual GitHub Actions workflow. It requires:

- `backup_tag`: an existing tag beginning with `world-backup-`
- `confirmation`: exact text `RESTORE WORLD`

After validating both inputs, it restores only `data/world.db`, `chronicle/`,
and the tracked summary file from the requested tag, commits the restored
state, and republishes Pages. It never restores application code or workflow
files.

## Security Boundaries

GitHub authentication and repository write permission are the authorization
boundary. Confirmation phrases prevent accidental clicks; they are not treated
as secrets. No password is embedded in static HTML. The existing server-only
`APP_PASSWORD` guard remains unchanged for API routes, but destructive reset
is no longer exposed by the dashboard UI.

## Testing

Tests verify public and dashboard reset controls are absent, the reset workflow
contains the required confirmation guard and backup tag creation, and the
restore workflow validates the tag prefix and restores only world-state paths.

## Non-goals

- No change to simulation, historian, LLM provider routing, or story content.
- No indefinite retention guarantee beyond Git repository tag retention.
