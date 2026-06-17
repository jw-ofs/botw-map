# Symbolic Alignment

This project uses **symbolic alignment** to maintain verifiable project state. Instead of relying on prose that drifts out of date, project truth is encoded as typed symbols with property edges (interlocks) that form a hash tree. Agents traverse semantics; machines verify hashes.

## Where Truth Lives

- **`symbols/manifest.json`** — Declarative symbol definitions. Read the `description` and `properties` fields to understand current project state. If a symbol lists `docs`, read those files for full context.
- **`symbols/manifest.lock`** — Generated hash tree. The `means` field on each symbol is a human-readable summary. The `status` field tells you if alignment holds. Do not reason about hex strings.

## How to Check Alignment

```bash
python scripts/align.py status    # Full human-readable report
python scripts/align.py check     # Machine check (exit 0=ok, 1=broken, 2=stale)
python scripts/align.py verify    # Semantic diff: what drifted, in property terms
```

Run `status` for a full snapshot. Run `verify` after you have made changes to see exactly which properties / docs / interlocks moved since the lock was written — `verify` names the drift in semantic terms (no hex), so you can tell whether you need to update a property, regenerate the lock, or fix a broken interlock.

## When Alignment Breaks

If `align.py check` reports broken interlocks or missing docs:

1. **Stop.** Do not proceed with stale context.
2. Read the status output to understand what changed.
3. Either fix the root cause (update properties, restore docs) or flag the issue.
4. Run `python scripts/align.py lock` after fixing to regenerate the lock.

## Updating Symbols

When you change project state that a symbol tracks:

1. Update the relevant properties in `symbols/manifest.json`
2. Update any interlocked symbols that reference changed properties
3. Run `python scripts/align.py lock` to regenerate the hash tree
4. Commit both `manifest.json` and `manifest.lock` together

---

## Review Gate

A PreToolUse hook (`.claude/hooks/require-review.sh`) enforces **review before implementation**. When active task documents exist in `Agents/TODO/Active/`, source file edits (`src/`, `k8s/`, `scripts/`, `config/`) are blocked until a corresponding review report exists in `Agents/Review-reports/`.

### Workflow

1. Create a task document in `Agents/TODO/Active/` with `## Status: Not Started`
2. Draft your implementation plan
3. Write a review report in `Agents/Review-reports/` that references the task filename
4. Implement (hook now allows source file edits)
5. Mark the task `## Status: Complete` when done

### Conventions

- Review reports must reference the task filename (e.g., `my-task.md`) in their body
- In strict mode (default), the review must also have ≥ `REVIEW_GATE_MIN_LINES` (default 10) meaningful lines and contain any `REVIEW_GATE_KEYWORDS` configured in env
- Tasks with `## Status: Complete` (case-insensitive) are skipped by the gate
- A task can declare a shared surface via a `Surface: <key>` line — when ≥2 active tasks declare the same registered surface (see `.claude/hooks/combined-surfaces.json`), a combined review is also required
- Ad-hoc work without task documents is not gated
- Non-source files (`Agents/`, `docs/`, `.claude/`) are always allowed

---

## Project-Specific Instructions

<!-- Add your project-specific Claude Code instructions below this line -->
