# Workspace Instructions

## Continuation

- Read `AGENT_HANDOFF.ru.md`, `analysis/driver_port/UI_PORT_PLAN.ru.md` and
  current acceptance reports before continuing the port. Later measured results
  take precedence over historical plans. Reuse verified artifacts; rebuild only
  when a source change or failed validation requires it.
- Preserve the frozen baseline and prior trial evidence. Use new candidate and
  trial IDs. Compilation, offline tests and hardware acceptance are distinct.
- The user's current restriction is no camera use. Do not open a camera or claim
  visual UI acceptance without a later explicit instruction allowing it.

## Keep Git Current

- This workspace is a local Git repository. Check `git status --short` before
  edits and before finishing each meaningful unit of work.
- Keep project sources, agent instructions, plans and current acceptance
  summaries tracked. Update the handoff and current UI plan when the next step,
  restrictions or measured results change.
- Commit completed, verified units of work with a descriptive message. Inspect
  the staged diff first and include the relevant verification in the commit
  message or handoff. Do not commit unrelated user changes without authorization.
- Keep the repository current at handoff: commit your completed changes and
  report any remaining uncommitted work and failed or unrun checks.
- Do not add generated payloads, firmware/ROM images, card backups, memory dumps,
  VM disks, camera captures, credentials or third-party checkouts. The ignore
  rules intentionally track only sources, documentation and selected summaries;
  add a deliberate exception for a small reproducible fixture when needed.
- Do not rewrite history, amend commits or push to a remote unless requested.
  Never discard existing changes to obtain a clean worktree.
