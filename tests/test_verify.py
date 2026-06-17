"""Tests for the verify subcommand (Phase 2.4)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from .conftest import aligned_manifest, run_align, write_doc, write_manifest


@pytest.fixture
def synced(tmp_path: Path) -> Path:
    write_manifest(tmp_path, aligned_manifest())
    write_doc(tmp_path, "docs/architecture.md", "# Arch\n")
    write_doc(tmp_path, "docs/deployment.md", "# Dep\n")
    run_align("lock", project_dir=tmp_path).assert_ok()
    return tmp_path


class TestVerify:
    def test_in_sync_returns_0(self, synced: Path):
        result = run_align("verify", project_dir=synced)
        result.assert_ok()
        assert "In sync" in result.stdout

    def test_property_drift_returns_2(self, synced: Path):
        m = aligned_manifest()
        m["symbols"]["architecture"]["properties"]["schema_version"] = 4
        m["symbols"]["deployment"]["properties"]["expects_schema"] = 4
        write_manifest(synced, m)
        result = run_align("verify", project_dir=synced)
        assert result.exit_code == 2
        assert "schema_version" in result.stdout
        assert "3" in result.stdout and "4" in result.stdout

    def test_broken_interlock_returns_1(self, synced: Path):
        m = aligned_manifest()
        m["symbols"]["architecture"]["properties"]["provider"] = "aws"
        write_manifest(synced, m)
        result = run_align("verify", project_dir=synced)
        assert result.exit_code == 1
        assert "PASS" in result.stdout and "FAIL" in result.stdout

    def test_missing_doc_returns_1(self, synced: Path):
        (synced / "docs" / "architecture.md").unlink()
        result = run_align("verify", project_dir=synced)
        assert result.exit_code == 1
        assert "MISSING" in result.stdout

    def test_doc_content_changed_returns_2(self, synced: Path):
        (synced / "docs" / "architecture.md").write_text("# Arch\n\nNew content.\n", encoding="utf-8")
        result = run_align("verify", project_dir=synced)
        assert result.exit_code == 2
        assert "content changed" in result.stdout

    def test_property_added_shown(self, synced: Path):
        m = aligned_manifest()
        m["symbols"]["architecture"]["properties"]["region"] = "us-east"
        write_manifest(synced, m)
        result = run_align("verify", project_dir=synced)
        assert "region" in result.stdout
        assert "us-east" in result.stdout

    def test_symbol_added(self, synced: Path):
        m = aligned_manifest()
        m["symbols"]["new_symbol"] = {
            "description": "new",
            "docs": [],
            "properties": {"key": "value"},
            "interlocks": {},
        }
        write_manifest(synced, m)
        result = run_align("verify", project_dir=synced)
        assert "ADDED" in result.stdout
        assert "new_symbol" in result.stdout

    def test_symbol_removed(self, synced: Path):
        m = aligned_manifest()
        del m["symbols"]["deployment"]
        write_manifest(synced, m)
        result = run_align("verify", project_dir=synced)
        assert "REMOVED" in result.stdout
        assert "deployment" in result.stdout

    def test_no_lock_returns_1(self, tmp_path: Path):
        write_manifest(tmp_path, aligned_manifest())
        result = run_align("verify", project_dir=tmp_path)
        assert result.exit_code == 1

    def test_type_error_returns_1(self, synced: Path):
        m = aligned_manifest()
        m["symbols"]["architecture"]["property_types"] = {"schema_version": "int"}
        m["symbols"]["architecture"]["properties"]["schema_version"] = "3"
        write_manifest(synced, m)
        result = run_align("verify", project_dir=synced)
        assert result.exit_code == 1
        assert "Type errors" in result.stdout or "TYPE" in result.stdout.upper()
