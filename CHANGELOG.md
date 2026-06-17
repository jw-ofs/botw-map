# Changelog

All notable changes to the Symbolic Alignment Template are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
this project uses semver for the template, independent of `version` inside any
particular `manifest.json`.

## [0.2.0] — 2026-05-11

This release closes the doc-vs-code credibility gaps identified in the v0.1
template review and adds expressivity (richer interlock operators, typed
properties, semantic drift reports, configurable gated paths).

### Added

- **`align.py verify` subcommand** — semantic diff between locked state and
  current state. Names property changes, doc edits, interlock-status
  transitions, and type errors in human terms (no hex output). Exit codes
  mirror `check`: 0 = in sync, 1 = broken, 2 = stale-but-consistent. Hex
  still drives drift detection internally; the output speaks `means`.
- **Long-form interlock operators** — beyond the implicit equality of the
  short-form string syntax, interlocks now accept
  `{"op": "<operator>", "local": "<property>"}` with operators:
  `eq`, `ne`, `gte`, `lte`, `in`, `matches` (regex), `exists`. Lock keys
  include the operator symbol so the lock is self-describing. Short-form
  remains valid as `eq` sugar — every v0.1 manifest still works unchanged.
- **Typed properties** — optional `property_types` map per symbol with
  specs `string`, `int`, `float`, `bool`, `enum:a|b|c`, `semver` (full
  SemVer 2.0 grammar). Catches drift like `3` silently becoming `"3"`.
  Type errors surface as a distinct `type_errors` field per symbol in the
  lock and as their own issue class in `check` / `verify` / `status`.
- **Configurable gated paths** — new top-level `gates.gated_paths` block
  in `manifest.json` controls which path prefixes the PreToolUse hooks
  guard. Resolution order: `REVIEW_GATE_GATED_PREFIXES` env var > manifest
  > defaults (`src/`, `k8s/`, `scripts/`, `config/`). Gate list is hashed
  alongside the rest of the manifest.
- **`align.py --project-dir <path>`** — explicit project-root override on
  every subcommand.
- **Project-root auto-discovery** — `align.py` walks parents from the
  script location to find `symbols/manifest.json`, with
  `$CLAUDE_PROJECT_DIR` as a fast path. Script works from any CWD.
- **`align.py lock --allow-broken`** — opt-in flag to suppress the
  non-zero exit code when the regenerated lock is broken.
- **Real test suite** — 111 behavioral tests across `tests/test_align.py`
  (24), `tests/test_alignment_gate.py` (6), `tests/test_review_gate.py`
  (21), `tests/test_operators.py` (21), `tests/test_typed_properties.py`
  (29), `tests/test_verify.py` (10). Tests drive every binary as a
  subprocess so the contract under test is the CLI surface — exit codes,
  stdout, stderr, hook stdin → decision JSON.
- **`alignment_gate.py`** and **`review_gate.py`** Python hook
  implementations. The `.sh` files are now thin bash shims that pipe
  stdin to the Python script. Drops the `jq` and `yq` dependencies.
- **CI matrix** — `.github/workflows/alignment-check.yml` now runs on
  Python 3.10, 3.11, and 3.12, and runs `pytest tests/` on each.
- **`Agents/TODO/Active/.gitkeep`** — preserves the empty directory in
  git so the review gate has somewhere to look on fresh checkouts.

### Changed

- **`align.py lock` exit code** — now returns 1 when the regenerated lock
  is broken (was 0 in v0.1). Use `--allow-broken` to opt out. CI scripts
  that depended on the v0.1 "always 0" behavior must be updated or use
  `--allow-broken`.
- **`align.py lock` missing-manifest exit code** — now returns 2 (was 1)
  to distinguish "manifest absent" from "alignment broken." Aligns with
  the new exit-code vocabulary.
- **`require-review.sh` enforcement** — previously did a `grep -q` on the
  task filename only, accepting a one-line review as valid. Now (in strict
  mode, the default) the review must:
  1. Reference the task filename in its body, AND
  2. Contain at least `REVIEW_GATE_MIN_LINES` (default 10) meaningful lines, AND
  3. Contain every keyword in `REVIEW_GATE_KEYWORDS` (default: none).
  Set `REVIEW_GATE_STRICT=false` to revert to filename-only matching
  during onboarding.
- **Combined-surface enforcement is now live.** Previously documented as
  enforced but no code read the registry. `review_gate.py` now:
  1. Loads surfaces from `.claude/hooks/combined-surfaces.json`.
  2. Parses `Surface: <key>` lines from each active task.
  3. When ≥2 active tasks declare the same registered surface key,
     requires the combined review file declared in the registry to
     exist with the registry-specified `minimum-lines` and
     `required-keywords`.
- **Hook path-pattern gating** — paths are normalized to project-relative
  POSIX form before matching, so absolute and relative paths both gate
  correctly. Previously the case-pattern (`*/src/*|*/k8s/*|...`) failed on
  paths like `src/foo.py` with no parent segment.
- **Hook CWD handling** — both hooks now pass `--project-dir` explicitly
  to `align.py`. The v0.1 hooks called `align.py` from whatever CWD they
  happened to be in, which broke `align.py`'s CWD-relative paths.
- **Lock format additions** (backward-compatible — new fields only):
  - Each symbol entry now includes a `properties` field with the raw
    property values, so `verify` can produce structured diffs. The values
    are also implicit in `means`; the new field is a structured copy.
  - Each symbol entry may include `type_errors` when typed properties
    fail validation.
  - Interlock keys now include the operator symbol (`==`, `>=`, `∈`,
    `=~`, `exists`) rather than always `==`.
- **`hash_file`** now streams in 64 KiB chunks instead of reading the
  entire file into memory.
- **stdout/stderr** are reconfigured to UTF-8 at startup so Windows pipes
  don't `UnicodeEncodeError` on the arrow / bullet glyphs.
- **README** — Python floor corrected from "3.9+" to "3.10+" (the codebase
  has always used PEP 604 `str | None` syntax). Command table includes
  `verify` and the new `lock` exit codes. Long-form operator and
  property-types syntax documented. Gated-paths configuration documented.
- **CLAUDE.md** — Review-gate conventions reflect actual enforcement
  (keywords, min lines, surface declaration). Mentions `verify`.
- **`docs/review-workflow.md`** — references `review_gate.py` and
  `combined-surfaces.json`; describes the actual enforcement rules.

### Fixed

- **`align.py` CWD bug** — script no longer assumes CWD is the project
  root. Works correctly whether invoked from a hook, from CI, or from
  a subdirectory.
- **Stale `.claude/settings.local.json`** — the v0.1 template shipped with
  a local file referencing the path `C:/dev/codex_baseline` (a rename
  artifact). The file is now `.gitignore`d and removed from the template.

### Removed

- **`.claude/hooks/combined-surfaces.yaml`** — replaced by
  `combined-surfaces.json` (stdlib JSON parsing; no YAML dependency).
  Comments that lived in the YAML file moved to `_help` and `_schema`
  keys inside the JSON file and to `docs/review-workflow.md`.
- **`jq` and `yq` runtime dependencies** in the hooks. The `.sh` files
  are now thin Python invocations.

### Migration from 0.1.x

For most users, **no manifest changes are required.** The short-form
interlock syntax and the absence of `property_types` / `gates` blocks
are fully backward-compatible.

If you depended on the lenient review gate:

- Add `REVIEW_GATE_STRICT=false` to the hook's environment for an
  onboarding period (or permanently, if filename-matching is enough).

If you depended on `align.py lock` always returning 0:

- Pass `--allow-broken`, or check `align.py check` separately.

If you scripted against the lock file structure:

- New per-symbol fields (`properties`, `type_errors`) are additive.
- Interlock keys now include the operator symbol — split on whitespace
  to recover the parts.

### Test coverage

```
tests/test_align.py             24 tests   CLI exit codes, all subcommands
tests/test_alignment_gate.py     6 tests   alignment hook deny/allow paths
tests/test_review_gate.py       21 tests   review hook, all enforcement modes
tests/test_operators.py         21 tests   every operator × pass/fail/type-error
tests/test_typed_properties.py  29 tests   every type spec × valid/invalid
tests/test_verify.py            10 tests   verify subcommand
total                          111 tests
```

CI runs the full suite on Python 3.10 / 3.11 / 3.12.

---

## [0.1.0] — Initial template

Initial release: declarative symbols with property interlocks, Merkle-style
hash tree in `manifest.lock`, PreToolUse hooks for alignment + review gates,
combined-scenario review workflow (documented, partially enforced).
