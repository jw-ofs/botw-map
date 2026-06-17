"""Behavioral tests for .claude/hooks/review_gate.py.

The hook reads a Claude Code PreToolUse event on stdin and emits a deny
decision on stdout when the review gate is unsatisfied. Tests drive it as a
subprocess with crafted stdin JSON.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

HOOK_SCRIPT = Path(__file__).resolve().parent.parent / ".claude" / "hooks" / "review_gate.py"


@dataclass
class HookResult:
    exit_code: int
    stdout: str
    stderr: str
    decision: dict | None  # parsed JSON if hook emitted a deny

    @property
    def is_allow(self) -> bool:
        return self.decision is None

    @property
    def is_deny(self) -> bool:
        return (
            self.decision is not None
            and self.decision.get("hookSpecificOutput", {}).get("permissionDecision") == "deny"
        )

    @property
    def deny_reason(self) -> str:
        if not self.is_deny:
            return ""
        return self.decision["hookSpecificOutput"]["permissionDecisionReason"]


def run_hook(
    file_path: str,
    project_root: Path,
    env_overrides: dict[str, str] | None = None,
) -> HookResult:
    """Invoke review_gate.py with a synthetic PreToolUse event."""
    event = {
        "tool_input": {"file_path": file_path},
        "cwd": str(project_root),
    }
    env = os.environ.copy()
    env.pop("CLAUDE_PROJECT_DIR", None)
    env["CLAUDE_PROJECT_DIR"] = str(project_root)
    if env_overrides:
        env.update(env_overrides)

    result = subprocess.run(
        [sys.executable, str(HOOK_SCRIPT)],
        input=json.dumps(event),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    decision = None
    if result.stdout.strip():
        try:
            decision = json.loads(result.stdout)
        except json.JSONDecodeError:
            decision = None
    return HookResult(result.returncode, result.stdout, result.stderr, decision)


# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def project(tmp_path: Path) -> Path:
    """Empty project skeleton: Agents/TODO/Active/, Agents/Review-reports/, src/."""
    (tmp_path / "Agents" / "TODO" / "Active").mkdir(parents=True)
    (tmp_path / "Agents" / "Review-reports").mkdir(parents=True)
    (tmp_path / "src").mkdir(parents=True)
    (tmp_path / ".claude" / "hooks").mkdir(parents=True)
    # Empty surfaces registry
    (tmp_path / ".claude" / "hooks" / "combined-surfaces.json").write_text(
        json.dumps({"combined-surfaces": []}), encoding="utf-8"
    )
    return tmp_path


def add_task(project: Path, name: str, status: str = "In Progress", surface: str | None = None) -> None:
    body = f"# Task\n\n## Status: {status}\n\nWork to do.\n"
    if surface:
        body += f"\nSurface: {surface}\n"
    (project / "Agents" / "TODO" / "Active" / name).write_text(body, encoding="utf-8")


def add_review(project: Path, name: str, body: str) -> None:
    (project / "Agents" / "Review-reports" / name).write_text(body, encoding="utf-8")


# ─── Path filtering ──────────────────────────────────────────────────────────

class TestPathFilter:
    def test_unrelated_path_allowed(self, project: Path):
        result = run_hook("docs/readme.md", project)
        assert result.is_allow

    def test_absolute_unrelated_path_allowed(self, project: Path):
        result = run_hook(str(project / "Agents" / "TODO" / "x.md"), project)
        assert result.is_allow

    def test_relative_src_path_gated(self, project: Path):
        # Active task without review → gated path should deny
        add_task(project, "task1.md")
        result = run_hook("src/foo.py", project)
        assert result.is_deny

    def test_absolute_src_path_gated(self, project: Path):
        add_task(project, "task1.md")
        result = run_hook(str(project / "src" / "foo.py"), project)
        assert result.is_deny

    def test_custom_prefixes_via_env(self, project: Path):
        add_task(project, "task1.md")
        # Override gated paths to only foo/
        result = run_hook(
            "src/foo.py",
            project,
            env_overrides={"REVIEW_GATE_GATED_PREFIXES": "foo/"},
        )
        assert result.is_allow

        result = run_hook(
            "foo/bar.py",
            project,
            env_overrides={"REVIEW_GATE_GATED_PREFIXES": "foo/"},
        )
        assert result.is_deny

    def test_manifest_gated_paths_override_defaults(self, project: Path):
        """gates.gated_paths in manifest should take effect when env is unset."""
        # Write a manifest with custom gated paths
        manifest = {
            "version": "1.0.0",
            "project": {"name": "t", "intent": "t"},
            "gates": {"gated_paths": ["api/", "infra/"]},
            "symbols": {},
        }
        (project / "symbols").mkdir(exist_ok=True)
        (project / "symbols" / "manifest.json").write_text(
            json.dumps(manifest), encoding="utf-8"
        )
        add_task(project, "task1.md")
        # src/ no longer gated
        result = run_hook("src/foo.py", project)
        assert result.is_allow
        # api/ now gated
        result = run_hook("api/bar.py", project)
        assert result.is_deny

    def test_env_overrides_manifest(self, project: Path):
        """Env var should win over manifest config."""
        manifest = {
            "version": "1.0.0",
            "project": {"name": "t", "intent": "t"},
            "gates": {"gated_paths": ["api/"]},
            "symbols": {},
        }
        (project / "symbols").mkdir(exist_ok=True)
        (project / "symbols" / "manifest.json").write_text(
            json.dumps(manifest), encoding="utf-8"
        )
        add_task(project, "task1.md")
        # Env wins — gate `lib/` instead of `api/`
        result = run_hook(
            "api/foo.py",
            project,
            env_overrides={"REVIEW_GATE_GATED_PREFIXES": "lib/"},
        )
        assert result.is_allow
        result = run_hook(
            "lib/foo.py",
            project,
            env_overrides={"REVIEW_GATE_GATED_PREFIXES": "lib/"},
        )
        assert result.is_deny


# ─── No active tasks ─────────────────────────────────────────────────────────

class TestNoActiveTasks:
    def test_no_tasks_dir_allowed(self, tmp_path: Path):
        # No Agents/TODO/Active at all
        result = run_hook("src/foo.py", tmp_path)
        assert result.is_allow

    def test_empty_tasks_dir_allowed(self, project: Path):
        result = run_hook("src/foo.py", project)
        assert result.is_allow

    def test_only_completed_tasks_allowed(self, project: Path):
        add_task(project, "done.md", status="Complete")
        result = run_hook("src/foo.py", project)
        assert result.is_allow


# ─── Per-task review validation ──────────────────────────────────────────────

class TestPerTaskReview:
    def test_active_task_without_review_denied(self, project: Path):
        add_task(project, "task1.md")
        result = run_hook("src/foo.py", project)
        assert result.is_deny
        assert "task1.md" in result.deny_reason

    def test_one_line_review_denied_in_strict_mode(self, project: Path):
        add_task(project, "task1.md")
        add_review(project, "task1-review.md", "task1.md")
        result = run_hook("src/foo.py", project)
        assert result.is_deny
        assert "thin" in result.deny_reason.lower() or "meaningful" in result.deny_reason.lower()

    def test_one_line_review_allowed_in_lenient_mode(self, project: Path):
        add_task(project, "task1.md")
        add_review(project, "task1-review.md", "task1.md")
        result = run_hook(
            "src/foo.py",
            project,
            env_overrides={"REVIEW_GATE_STRICT": "false"},
        )
        assert result.is_allow

    def test_full_review_allowed(self, project: Path):
        add_task(project, "task1.md")
        body = "# Review for task1.md\n\n" + "\n".join(
            f"Finding {i}: looks fine." for i in range(20)
        )
        add_review(project, "task1-review.md", body)
        result = run_hook("src/foo.py", project)
        assert result.is_allow

    def test_review_missing_keyword_denied(self, project: Path):
        add_task(project, "task1.md")
        body = "# Review for task1.md\n\n" + "\n".join(
            f"Finding {i}: looks fine." for i in range(20)
        )
        add_review(project, "task1-review.md", body)
        result = run_hook(
            "src/foo.py",
            project,
            env_overrides={"REVIEW_GATE_KEYWORDS": "logic,schema"},
        )
        assert result.is_deny
        assert "keyword" in result.deny_reason.lower()

    def test_review_with_keywords_allowed(self, project: Path):
        add_task(project, "task1.md")
        body = (
            "# Review for task1.md\n\n"
            "Logic check: ok.\nSchema check: ok.\n"
            + "\n".join(f"Detail {i}." for i in range(20))
        )
        add_review(project, "task1-review.md", body)
        result = run_hook(
            "src/foo.py",
            project,
            env_overrides={"REVIEW_GATE_KEYWORDS": "logic,schema"},
        )
        assert result.is_allow


# ─── Combined-surfaces ───────────────────────────────────────────────────────

class TestCombinedSurfaces:
    def _add_surface(self, project: Path, key: str, review_path: str) -> None:
        cfg = {
            "combined-surfaces": [
                {
                    "key": key,
                    "review-file": review_path,
                    "minimum-lines": 5,
                    "required-keywords": ["compound", "shared-state"],
                }
            ]
        }
        (project / ".claude" / "hooks" / "combined-surfaces.json").write_text(
            json.dumps(cfg), encoding="utf-8"
        )

    def _valid_per_task_review(self, project: Path, task_name: str) -> None:
        body = f"# Review for {task_name}\n\n" + "\n".join(
            f"Finding {i}." for i in range(20)
        )
        add_review(project, f"{task_name}-review.md", body)

    def test_single_task_on_surface_no_combined_review_needed(self, project: Path):
        self._add_surface(project, "shared-tick", "Agents/Review-reports/shared-tick-combined.md")
        add_task(project, "task1.md", surface="shared-tick")
        self._valid_per_task_review(project, "task1.md")
        result = run_hook("src/foo.py", project)
        assert result.is_allow

    def test_two_tasks_on_surface_without_combined_review_denied(self, project: Path):
        self._add_surface(project, "shared-tick", "Agents/Review-reports/shared-tick-combined.md")
        add_task(project, "task1.md", surface="shared-tick")
        add_task(project, "task2.md", surface="shared-tick")
        self._valid_per_task_review(project, "task1.md")
        self._valid_per_task_review(project, "task2.md")
        result = run_hook("src/foo.py", project)
        assert result.is_deny
        assert "COMBINED REVIEW MISSING" in result.deny_reason

    def test_two_tasks_with_combined_review_allowed(self, project: Path):
        self._add_surface(project, "shared-tick", "Agents/Review-reports/shared-tick-combined.md")
        add_task(project, "task1.md", surface="shared-tick")
        add_task(project, "task2.md", surface="shared-tick")
        self._valid_per_task_review(project, "task1.md")
        self._valid_per_task_review(project, "task2.md")
        # Provide combined review with required keywords + enough lines
        combined = (
            "# Combined review\n\n"
            "compound diff analysis.\nshared-state audit.\n"
            + "\n".join(f"Item {i}." for i in range(10))
        )
        (project / "Agents" / "Review-reports" / "shared-tick-combined.md").write_text(
            combined, encoding="utf-8"
        )
        result = run_hook("src/foo.py", project)
        assert result.is_allow

    def test_combined_review_missing_keywords_denied(self, project: Path):
        self._add_surface(project, "shared-tick", "Agents/Review-reports/shared-tick-combined.md")
        add_task(project, "task1.md", surface="shared-tick")
        add_task(project, "task2.md", surface="shared-tick")
        self._valid_per_task_review(project, "task1.md")
        self._valid_per_task_review(project, "task2.md")
        combined = "# Combined review\n\n" + "\n".join(f"Item {i}." for i in range(20))
        (project / "Agents" / "Review-reports" / "shared-tick-combined.md").write_text(
            combined, encoding="utf-8"
        )
        result = run_hook("src/foo.py", project)
        assert result.is_deny
        assert "KEYWORDS" in result.deny_reason

    def test_tasks_on_different_surfaces_not_combined(self, project: Path):
        cfg = {
            "combined-surfaces": [
                {"key": "a", "review-file": "Agents/Review-reports/a.md", "minimum-lines": 5, "required-keywords": []},
                {"key": "b", "review-file": "Agents/Review-reports/b.md", "minimum-lines": 5, "required-keywords": []},
            ]
        }
        (project / ".claude" / "hooks" / "combined-surfaces.json").write_text(
            json.dumps(cfg), encoding="utf-8"
        )
        add_task(project, "task1.md", surface="a")
        add_task(project, "task2.md", surface="b")
        self._valid_per_task_review(project, "task1.md")
        self._valid_per_task_review(project, "task2.md")
        result = run_hook("src/foo.py", project)
        assert result.is_allow
