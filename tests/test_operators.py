"""Tests for the richer interlock operators (Phase 2.1)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from .conftest import aligned_manifest, run_align, write_doc, write_manifest


def _bare_manifest_with(interlocks: dict, deployment_props: dict | None = None,
                        architecture_props: dict | None = None) -> dict:
    """Build a two-symbol manifest with the given interlocks on `deployment`."""
    return {
        "version": "1.0.0",
        "project": {"name": "test", "intent": "testing"},
        "symbols": {
            "architecture": {
                "description": "core",
                "docs": [],
                "properties": architecture_props or {"provider": "akamai", "schema_version": 3},
                "interlocks": {},
            },
            "deployment": {
                "description": "deploy",
                "docs": [],
                "properties": deployment_props or {"expects_provider": "akamai", "expects_schema": 3},
                "interlocks": interlocks,
            },
        },
    }


@pytest.fixture
def proj(tmp_path: Path) -> Path:
    return tmp_path


# ─── Backward compatibility: short-form string still means eq ────────────────

class TestShortForm:
    def test_short_form_equality_still_works(self, proj: Path):
        m = _bare_manifest_with({"architecture.provider": "expects_provider"})
        write_manifest(proj, m)
        result = run_align("lock", project_dir=proj)
        result.assert_ok()
        lock = json.loads((proj / "symbols" / "manifest.lock").read_text())
        # Key includes operator now
        keys = list(lock["symbols"]["deployment"]["interlocks"].keys())
        assert any("==" in k for k in keys)
        assert all(v == "PASS" for v in lock["symbols"]["deployment"]["interlocks"].values())


# ─── eq / ne ──────────────────────────────────────────────────────────────────

class TestEqNe:
    def test_long_form_eq_pass(self, proj: Path):
        m = _bare_manifest_with({
            "architecture.provider": {"op": "eq", "local": "expects_provider"}
        })
        write_manifest(proj, m)
        result = run_align("lock", project_dir=proj)
        result.assert_ok()

    def test_long_form_ne_pass(self, proj: Path):
        m = _bare_manifest_with(
            {"architecture.provider": {"op": "ne", "local": "expects_provider"}},
            deployment_props={"expects_provider": "aws", "expects_schema": 3},
        )
        write_manifest(proj, m)
        result = run_align("lock", project_dir=proj)
        result.assert_ok()

    def test_long_form_ne_fail(self, proj: Path):
        m = _bare_manifest_with(
            {"architecture.provider": {"op": "ne", "local": "expects_provider"}},
        )
        write_manifest(proj, m)
        result = run_align("lock", project_dir=proj)
        assert result.exit_code == 1


# ─── gte / lte ────────────────────────────────────────────────────────────────

class TestNumericComparison:
    def test_gte_pass(self, proj: Path):
        m = _bare_manifest_with(
            {"architecture.schema_version": {"op": "gte", "local": "expects_schema"}},
            architecture_props={"provider": "akamai", "schema_version": 5},
            deployment_props={"expects_provider": "akamai", "expects_schema": 3},
        )
        write_manifest(proj, m)
        result = run_align("lock", project_dir=proj)
        result.assert_ok()

    def test_gte_fail(self, proj: Path):
        m = _bare_manifest_with(
            {"architecture.schema_version": {"op": "gte", "local": "expects_schema"}},
            architecture_props={"provider": "akamai", "schema_version": 2},
            deployment_props={"expects_provider": "akamai", "expects_schema": 3},
        )
        write_manifest(proj, m)
        result = run_align("lock", project_dir=proj)
        assert result.exit_code == 1

    def test_gte_type_error_on_string(self, proj: Path):
        m = _bare_manifest_with(
            {"architecture.provider": {"op": "gte", "local": "expects_provider"}},
        )
        write_manifest(proj, m)
        result = run_align("lock", project_dir=proj)
        assert result.exit_code == 1
        # status surfaces TYPE_ERROR
        lock = json.loads((proj / "symbols" / "manifest.lock").read_text())
        statuses = list(lock["symbols"]["deployment"]["interlocks"].values())
        assert "TYPE_ERROR" in statuses

    def test_lte_pass(self, proj: Path):
        m = _bare_manifest_with(
            {"architecture.schema_version": {"op": "lte", "local": "expects_schema"}},
            architecture_props={"provider": "akamai", "schema_version": 2},
            deployment_props={"expects_provider": "akamai", "expects_schema": 3},
        )
        write_manifest(proj, m)
        result = run_align("lock", project_dir=proj)
        result.assert_ok()


# ─── in ───────────────────────────────────────────────────────────────────────

class TestIn:
    def test_in_pass(self, proj: Path):
        m = _bare_manifest_with(
            {"architecture.provider": {"op": "in", "local": "supported_providers"}},
            deployment_props={
                "expects_provider": "akamai",
                "expects_schema": 3,
                "supported_providers": ["akamai", "aws", "gcp"],
            },
        )
        write_manifest(proj, m)
        result = run_align("lock", project_dir=proj)
        result.assert_ok()

    def test_in_fail(self, proj: Path):
        m = _bare_manifest_with(
            {"architecture.provider": {"op": "in", "local": "supported_providers"}},
            deployment_props={
                "expects_provider": "akamai",
                "expects_schema": 3,
                "supported_providers": ["aws", "gcp"],
            },
        )
        write_manifest(proj, m)
        result = run_align("lock", project_dir=proj)
        assert result.exit_code == 1

    def test_in_type_error_when_local_not_list(self, proj: Path):
        m = _bare_manifest_with(
            {"architecture.provider": {"op": "in", "local": "expects_provider"}},
        )
        write_manifest(proj, m)
        result = run_align("lock", project_dir=proj)
        assert result.exit_code == 1


# ─── matches ──────────────────────────────────────────────────────────────────

class TestMatches:
    def test_matches_pass(self, proj: Path):
        m = _bare_manifest_with(
            {"architecture.provider": {"op": "matches", "local": "provider_pattern"}},
            deployment_props={
                "expects_provider": "akamai",
                "expects_schema": 3,
                "provider_pattern": r"^aka",
            },
        )
        write_manifest(proj, m)
        result = run_align("lock", project_dir=proj)
        result.assert_ok()

    def test_matches_fail(self, proj: Path):
        m = _bare_manifest_with(
            {"architecture.provider": {"op": "matches", "local": "provider_pattern"}},
            deployment_props={
                "expects_provider": "akamai",
                "expects_schema": 3,
                "provider_pattern": r"^aws",
            },
        )
        write_manifest(proj, m)
        result = run_align("lock", project_dir=proj)
        assert result.exit_code == 1

    def test_matches_bad_regex_is_type_error(self, proj: Path):
        m = _bare_manifest_with(
            {"architecture.provider": {"op": "matches", "local": "provider_pattern"}},
            deployment_props={
                "expects_provider": "akamai",
                "expects_schema": 3,
                "provider_pattern": "[unclosed",
            },
        )
        write_manifest(proj, m)
        result = run_align("lock", project_dir=proj)
        assert result.exit_code == 1


# ─── exists ───────────────────────────────────────────────────────────────────

class TestExists:
    def test_exists_pass(self, proj: Path):
        m = _bare_manifest_with(
            {"architecture.provider": {"op": "exists"}},
        )
        write_manifest(proj, m)
        result = run_align("lock", project_dir=proj)
        result.assert_ok()

    def test_exists_fail_when_property_missing(self, proj: Path):
        m = _bare_manifest_with(
            {"architecture.nonexistent": {"op": "exists"}},
        )
        write_manifest(proj, m)
        result = run_align("lock", project_dir=proj)
        assert result.exit_code == 1

    def test_exists_fail_when_value_is_null(self, proj: Path):
        m = _bare_manifest_with(
            {"architecture.maybe_null": {"op": "exists"}},
            architecture_props={"provider": "akamai", "schema_version": 3, "maybe_null": None},
        )
        write_manifest(proj, m)
        result = run_align("lock", project_dir=proj)
        assert result.exit_code == 1


# ─── Malformed long-form ──────────────────────────────────────────────────────

class TestMalformedInterlocks:
    def test_unknown_op_invalid(self, proj: Path):
        m = _bare_manifest_with(
            {"architecture.provider": {"op": "frobnicate", "local": "expects_provider"}},
        )
        write_manifest(proj, m)
        result = run_align("lock", project_dir=proj)
        assert result.exit_code == 1
        lock = json.loads((proj / "symbols" / "manifest.lock").read_text())
        statuses = list(lock["symbols"]["deployment"]["interlocks"].values())
        assert "INVALID_INTERLOCK" in statuses

    def test_missing_local_field_invalid(self, proj: Path):
        m = _bare_manifest_with(
            {"architecture.provider": {"op": "eq"}},
        )
        write_manifest(proj, m)
        result = run_align("lock", project_dir=proj)
        assert result.exit_code == 1

    def test_non_string_non_object_value_invalid(self, proj: Path):
        m = _bare_manifest_with(
            {"architecture.provider": 42},
        )
        write_manifest(proj, m)
        result = run_align("lock", project_dir=proj)
        assert result.exit_code == 1


# ─── Mixed short-form and long-form in same manifest ─────────────────────────

class TestMixedForms:
    def test_short_and_long_can_coexist(self, proj: Path):
        m = _bare_manifest_with({
            "architecture.provider": "expects_provider",  # short
            "architecture.schema_version": {"op": "gte", "local": "expects_schema"},  # long
        })
        write_manifest(proj, m)
        result = run_align("lock", project_dir=proj)
        result.assert_ok()
