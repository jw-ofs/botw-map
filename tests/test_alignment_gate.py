"""Behavioral tests for .claude/hooks/alignment_gate.py."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

from .conftest import aligned_manifest, run_align, write_doc, write_manifest

HOOK_SCRIPT = Path(__file__).resolve().parent.parent / ".claude" / "hooks" / "alignment_gate.py"
REAL_ALIGN_SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "align.py"


@dataclass
class HookResult:
    exit_code: int
    stdout: str
    stderr: str
    decision: dict | None

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


def run_alignment_hook(file_path: str, project_root: Path) -> HookResult:
    event = {"tool_input": {"file_path": file_path}, "cwd": str(project_root)}
    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = str(project_root)
    proc = subprocess.run(
        [sys.executable, str(HOOK_SCRIPT)],
        input=json.dumps(event),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    decision = None
    if proc.stdout.strip():
        try:
            decision = json.loads(proc.stdout)
        except json.JSONDecodeError:
            pass
    return HookResult(proc.returncode, proc.stdout, proc.stderr, decision)


@pytest.fixture
def aligned_project(tmp_path: Path) -> Path:
    """A tmp project with align.py present, aligned manifest, and the hook copied in."""
    # Copy align.py and the hook into tmp so the hook can find it via project_root
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()
    shutil.copy(REAL_ALIGN_SCRIPT, scripts_dir / "align.py")

    write_manifest(tmp_path, aligned_manifest())
    write_doc(tmp_path, "docs/architecture.md", "# Arch\n")
    write_doc(tmp_path, "docs/deployment.md", "# Dep\n")
    result = run_align("lock", project_dir=tmp_path)
    result.assert_ok()
    return tmp_path


class TestAlignmentGate:
    def test_non_source_path_allowed(self, aligned_project: Path):
        result = run_alignment_hook("docs/readme.md", aligned_project)
        assert result.is_allow

    def test_aligned_source_path_allowed(self, aligned_project: Path):
        result = run_alignment_hook("src/foo.py", aligned_project)
        assert result.is_allow

    def test_broken_alignment_denied(self, aligned_project: Path):
        # Break the interlock
        m = aligned_manifest()
        m["symbols"]["architecture"]["properties"]["provider"] = "aws"
        write_manifest(aligned_project, m)
        result = run_alignment_hook("src/foo.py", aligned_project)
        assert result.is_deny
        assert "BROKEN" in result.deny_reason

    def test_stale_lock_denied(self, aligned_project: Path):
        # Mutate properties without re-locking (keeping interlocks valid)
        m = aligned_manifest()
        m["symbols"]["architecture"]["properties"]["schema_version"] = 4
        m["symbols"]["deployment"]["properties"]["expects_schema"] = 4
        write_manifest(aligned_project, m)
        result = run_alignment_hook("src/foo.py", aligned_project)
        assert result.is_deny
        assert "STALE" in result.deny_reason

    def test_absolute_path_normalized_and_gated(self, aligned_project: Path):
        m = aligned_manifest()
        m["symbols"]["architecture"]["properties"]["provider"] = "aws"
        write_manifest(aligned_project, m)
        abs_path = str(aligned_project / "src" / "foo.py")
        result = run_alignment_hook(abs_path, aligned_project)
        assert result.is_deny

    def test_missing_align_script_allows(self, tmp_path: Path):
        # No scripts/align.py — hook should allow rather than block
        result = run_alignment_hook("src/foo.py", tmp_path)
        assert result.is_allow
