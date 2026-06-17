"""Shared pytest fixtures for align.py tests.

Tests drive align.py as a subprocess to exercise the real CLI surface — exit
codes, stdout/stderr, project-root resolution. We never import align.py as a
module; the contract under test is behavioral.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "align.py"


@dataclass
class CliResult:
    """Captured output of an align.py subprocess invocation."""

    exit_code: int
    stdout: str
    stderr: str

    def assert_ok(self) -> None:
        assert self.exit_code == 0, (
            f"expected exit 0, got {self.exit_code}\n"
            f"stdout:\n{self.stdout}\nstderr:\n{self.stderr}"
        )


def run_align(
    *args: str,
    project_dir: Path | None = None,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
) -> CliResult:
    """Run scripts/align.py with the given args. Returns CliResult."""
    cmd = [sys.executable, str(SCRIPT)]
    if project_dir is not None:
        cmd += ["--project-dir", str(project_dir)]
    cmd += list(args)

    full_env = os.environ.copy()
    # Drop CLAUDE_PROJECT_DIR from inherited env unless the test sets it
    full_env.pop("CLAUDE_PROJECT_DIR", None)
    if env:
        full_env.update(env)

    result = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        env=full_env,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return CliResult(result.returncode, result.stdout, result.stderr)


def write_manifest(root: Path, manifest: dict[str, Any]) -> None:
    """Write a manifest dict to <root>/symbols/manifest.json."""
    (root / "symbols").mkdir(parents=True, exist_ok=True)
    (root / "symbols" / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )


def write_doc(root: Path, rel_path: str, content: str = "# Doc\n") -> None:
    """Write a doc file relative to project root."""
    p = root / rel_path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


def aligned_manifest() -> dict[str, Any]:
    """A minimal manifest with one passing interlock."""
    return {
        "version": "1.0.0",
        "project": {"name": "test", "intent": "testing"},
        "symbols": {
            "architecture": {
                "description": "core",
                "docs": ["docs/architecture.md"],
                "properties": {"provider": "akamai", "schema_version": 3},
                "interlocks": {},
            },
            "deployment": {
                "description": "deploy",
                "docs": ["docs/deployment.md"],
                "properties": {"expects_provider": "akamai", "expects_schema": 3},
                "interlocks": {
                    "architecture.provider": "expects_provider",
                    "architecture.schema_version": "expects_schema",
                },
            },
        },
    }


@pytest.fixture
def fresh_project(tmp_path: Path) -> Path:
    """A tmp dir with a valid manifest, docs, and a freshly generated lock."""
    write_manifest(tmp_path, aligned_manifest())
    write_doc(tmp_path, "docs/architecture.md", "# Architecture\n\nakamai, schema 3.\n")
    write_doc(tmp_path, "docs/deployment.md", "# Deployment\n\nakamai, schema 3.\n")
    result = run_align("lock", project_dir=tmp_path)
    result.assert_ok()
    return tmp_path


@pytest.fixture
def empty_dir(tmp_path: Path) -> Path:
    """An empty tmp dir with no manifest."""
    return tmp_path
