# Symbolic Alignment Template

A framework for maintaining verifiable project state through declarative symbols. Instead of prose that rots over time, project truth is encoded as **typed symbols** with **property interlocks** that form a Merkle-like hash tree.

**Agents traverse semantics. Machines verify hashes.**

## What is Symbolic Alignment?

Traditional project documentation drifts. A decision made in week 1 gets buried in a doc nobody updates, and by week 8 an AI agent (or a human) is working from stale context.

Symbolic alignment fixes this by:

1. **Declaring truth as symbols** — each symbol has typed properties representing desired state
2. **Linking symbols with interlocks** — property edges that enforce consistency across symbols
3. **Hashing everything into a lock file** — a Merkle-like tree that CI and hooks can verify instantly
4. **Giving agents semantic handles** — the `description` and `means` fields let AI agents understand state without parsing hex

## Quick Start

1. **Use this template** — fork or clone this repository

2. **Customize `symbols/manifest.json`** — define your project's symbols, properties, and interlocks

3. **Create your docs** — add referenced documentation to `docs/`

4. **Generate the lock**:
   ```bash
   python scripts/align.py lock
   ```

5. **Commit both files** — `manifest.json` and `manifest.lock` travel together

Or start fresh with defaults:
```bash
python scripts/align.py init
```

## Defining Symbols

Each symbol in `manifest.json` has:

```json
{
  "symbol_name": {
    "description": "Human/agent-readable context about this symbol",
    "docs": ["docs/relevant-doc.md"],
    "properties": {
      "key": "value"
    },
    "property_types": {
      "key": "string"
    },
    "interlocks": {}
  }
}
```

- **`description`** — Semantic context. Agents read this to understand what the symbol represents.
- **`docs`** — File paths this symbol governs. These get hashed into the lock.
- **`properties`** — Key-value pairs representing desired state. These are what interlocks check.
- **`property_types`** *(optional)* — Map of property → type spec. Catches drift like `3` silently becoming `"3"`. Supported specs: `string`, `int`, `float`, `bool`, `enum:a|b|c`, `semver`.

## Defining Interlocks

Interlocks are directed edges between symbol properties. They enforce that two symbols agree on shared state.

### Short form (equality)

```json
"interlocks": {
  "architecture.provider": "expects_provider"
}
```

Reads as **"deployment.expects_provider must equal architecture.provider."** If someone changes `architecture.provider` to `"aws"` but forgets to update `deployment.expects_provider`, alignment breaks.

### Long form (any operator)

```json
"interlocks": {
  "architecture.schema_version": {"op": "gte", "local": "expects_schema"},
  "feature_flags.enabled":       {"op": "in",  "local": "required_flags"},
  "secrets.token":               {"op": "exists"}
}
```

Operators:

| Operator | Meaning |
|---|---|
| `eq` | foreign == local *(default, short-form sugar)* |
| `ne` | foreign != local |
| `gte` | foreign >= local *(numeric)* |
| `lte` | foreign <= local *(numeric)* |
| `in` | foreign ∈ local list |
| `matches` | `re.search(local_pattern, str(foreign))` matches |
| `exists` | foreign property is present and not null *(local is optional)* |

## Gated Paths

Hooks gate edits under specific path prefixes. The default is `src/`, `k8s/`, `scripts/`, `config/`. To override, add a `gates` block to `manifest.json`:

```json
"gates": {
  "gated_paths": ["api/", "infra/", "scripts/"]
}
```

Or set `REVIEW_GATE_GATED_PREFIXES=api/,infra/` to override per-environment (env wins over manifest).

## Using with Claude Code

The template includes:

- **`CLAUDE.md`** — Agent instructions that point to `manifest.json` as the source of truth
- **`.claude/settings.json`** — A `PreToolUse` hook that runs `align.py check --quiet` before any file edit, warning agents if alignment is broken

The hook is non-blocking by default (`|| true`). To make it blocking, remove the `|| true` from the hook command.

## CI Integration

The included GitHub Actions workflow (`.github/workflows/alignment-check.yml`) runs on every push and PR to `main`:

- Executes `python scripts/align.py check`
- Fails the workflow if interlocks are broken or docs are missing
- Posts a status report as a job summary on failure

## Commands Reference

| Command | Description |
|---|---|
| `align.py init` | Create starter `manifest.json`, placeholder docs, and initial `manifest.lock` |
| `align.py init --force` | Overwrite existing manifest |
| `align.py lock` | Regenerate `manifest.lock`. Exit 0 = aligned, 1 = lock written but broken, 2 = manifest missing |
| `align.py lock --allow-broken` | Exit 0 even when the regenerated lock is broken |
| `align.py check` | Verify alignment. Exit 0 = aligned, 1 = broken, 2 = stale |
| `align.py check --quiet` | One-line output to stderr (for hooks/CI) |
| `align.py verify` | Semantic diff between locked and current state — property/doc/interlock changes named explicitly (no hex). Exit 0 = sync, 1 = broken, 2 = stale |
| `align.py status` | Human-readable report with color-coded output |

All subcommands accept `--project-dir <path>` to override project-root discovery (otherwise resolved from `$CLAUDE_PROJECT_DIR` or by walking parents from the script).

## Review Workflow

The template includes a reviewer-gated workflow for non-trivial source changes, enforced by `.claude/hooks/require-review.sh`. Any edit under `src/`, `k8s/`, `scripts/`, or `config/` requires a committed plan and a committed independent review before the hook permits the edit.

A combined-scenario review extension catches compound regressions when multiple tasks modify the same shared surface. See:

- [`docs/review-workflow.md`](docs/review-workflow.md) — the full plan → review → combined-review flow
- [`docs/case-study-compound-regression.md`](docs/case-study-compound-regression.md) — the incident that motivated the combined-scenario extension
- [`.claude/hooks/combined-surfaces.json`](.claude/hooks/combined-surfaces.json) — registered shared-surface definitions (empty by default; operators register surfaces as interaction risk becomes apparent)
- [`Agents/Review-reports/TEMPLATE-combined-review.md`](Agents/Review-reports/TEMPLATE-combined-review.md) — reviewer's starting template for a combined-scenario review

## Requirements

- Python 3.10+ (stdlib only for `align.py` — no dependencies). The review-gate hook uses stdlib only as well.
