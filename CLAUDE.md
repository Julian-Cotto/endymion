# Endymion workspace — working agreement & conventions

Multi-submodule workspace. Feature modules each ship a `*-backend` (FastAPI)
and `*-frontend` (React micro-frontend) pair, mounted into the platform shell.
Active examples: `feature-asset-inventory-*`, `feature-reports-layering/*`,
`feature-continued-education-*`, `app-platform-*`.

## Working agreement — act, don't re-ask

Default to **executing** rather than pausing to confirm. Specifically:

- **Once we've agreed on an approach, build it end to end.** Do not stop after
  each file or step to ask "should I continue?" — carry the agreed solution
  through to a verified, working state, then report what was done.
- **Don't re-litigate settled decisions.** If the approach, scope, or a choice
  was already decided earlier in the conversation (or in an audit/plan doc we're
  following), treat it as final and proceed.
- **Make sensible default choices on reversible details** (naming, file
  placement, which existing pattern to copy) instead of asking. State the choice
  in your summary; don't turn it into a question.
- **Batch the verification, not the permission.** Prefer running the full
  build/test/typecheck and reporting results over asking whether you may run it.

Still pause for: destructive/irreversible actions (history rewrite, force-push,
bulk delete, dropping data), anything outward-facing (opening PRs, pushing to
shared branches, sending to external services), rotating/committing secrets, or
a genuine fork where the user's intent is unknown. When unsure whether something
is reversible, look before acting rather than asking.

## Permission prompts

Harness permission **dialogs** on tool calls come from `.claude/settings.json`
(project) and `~/.claude/settings.json` (global) — not this file. The project
allowlist is already broad. If a routine, safe command still prompts, add it to
the project `allow` list rather than working around it. Note: an env-var prefix
changes the match (`FOO=bar python …` is not `Bash(python *)`), so prefer
`env FOO=bar python …` or export first when you want an allowlisted match.

## Verify before declaring done

- **Python backends:** `pytest -q`; boot-smoke with the app factory when routes
  or models changed. Schema is managed by boot-time lightweight migrations
  (`create_all` + `ALTER TABLE` in `main.py`) unless a module has Alembic — new
  tables auto-create, added columns need a migration entry.
- **React frontends:** `npx tsc --noEmit`, `npx vitest run`, and `npm run build`
  (builds both the standalone `app` and the `mf` micro-frontend bundle).
- Frontend CSS lives in the **host shell**, not the module — the standalone
  build renders unstyled by design. Match the shell's existing utility classes
  (`stack-lg`, `card`, `section-block`, `badge*`, `heading-*`, `SectionHeader`,
  chips) rather than inventing styles.

## Docs

Audit / plan docs live at the workspace root (`ASSET_INVENTORY_AUDIT*.md`, etc.).
When following one, update its status inline as work ships.
