"""Tests for typed properties (Phase 2.2)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from .conftest import run_align, write_manifest


def _manifest(props: dict, types: dict) -> dict:
    return {
        "version": "1.0.0",
        "project": {"name": "test", "intent": "testing"},
        "symbols": {
            "x": {
                "description": "x",
                "docs": [],
                "properties": props,
                "property_types": types,
                "interlocks": {},
            },
        },
    }


@pytest.fixture
def proj(tmp_path: Path) -> Path:
    return tmp_path


class TestStringType:
    def test_string_pass(self, proj: Path):
        write_manifest(proj, _manifest({"name": "alice"}, {"name": "string"}))
        run_align("lock", project_dir=proj).assert_ok()

    def test_string_fail_on_int(self, proj: Path):
        write_manifest(proj, _manifest({"name": 42}, {"name": "string"}))
        result = run_align("lock", project_dir=proj)
        assert result.exit_code == 1


class TestIntType:
    def test_int_pass(self, proj: Path):
        write_manifest(proj, _manifest({"n": 3}, {"n": "int"}))
        run_align("lock", project_dir=proj).assert_ok()

    def test_int_fail_on_string(self, proj: Path):
        # The classic "3 vs '3' drift" case
        write_manifest(proj, _manifest({"n": "3"}, {"n": "int"}))
        result = run_align("lock", project_dir=proj)
        assert result.exit_code == 1
        lock = json.loads((proj / "symbols" / "manifest.lock").read_text())
        assert "type_errors" in lock["symbols"]["x"]
        assert "n" in lock["symbols"]["x"]["type_errors"]

    def test_int_fail_on_bool(self, proj: Path):
        # bool is a subclass of int in Python — we explicitly disallow it
        write_manifest(proj, _manifest({"n": True}, {"n": "int"}))
        result = run_align("lock", project_dir=proj)
        assert result.exit_code == 1


class TestBoolType:
    def test_bool_pass(self, proj: Path):
        write_manifest(proj, _manifest({"on": True}, {"on": "bool"}))
        run_align("lock", project_dir=proj).assert_ok()

    def test_bool_fail_on_int(self, proj: Path):
        write_manifest(proj, _manifest({"on": 1}, {"on": "bool"}))
        result = run_align("lock", project_dir=proj)
        assert result.exit_code == 1


class TestFloatType:
    def test_float_accepts_int(self, proj: Path):
        # int is widening to float
        write_manifest(proj, _manifest({"f": 3}, {"f": "float"}))
        run_align("lock", project_dir=proj).assert_ok()

    def test_float_accepts_float(self, proj: Path):
        write_manifest(proj, _manifest({"f": 3.14}, {"f": "float"}))
        run_align("lock", project_dir=proj).assert_ok()

    def test_float_rejects_string(self, proj: Path):
        write_manifest(proj, _manifest({"f": "3.14"}, {"f": "float"}))
        result = run_align("lock", project_dir=proj)
        assert result.exit_code == 1


class TestEnumType:
    def test_enum_pass(self, proj: Path):
        write_manifest(proj, _manifest(
            {"env": "production"}, {"env": "enum:dev|staging|production"},
        ))
        run_align("lock", project_dir=proj).assert_ok()

    def test_enum_fail(self, proj: Path):
        write_manifest(proj, _manifest(
            {"env": "qa"}, {"env": "enum:dev|staging|production"},
        ))
        result = run_align("lock", project_dir=proj)
        assert result.exit_code == 1


class TestSemverType:
    @pytest.mark.parametrize("version", ["1.0.0", "0.1.0", "10.20.30", "1.2.3-alpha", "1.2.3+build.1", "1.2.3-rc.1+sha.abc"])
    def test_semver_pass(self, proj: Path, version: str):
        write_manifest(proj, _manifest({"v": version}, {"v": "semver"}))
        run_align("lock", project_dir=proj).assert_ok()

    @pytest.mark.parametrize("version", ["1.0", "v1.0.0", "1.0.0.0", "1.0.0-", "abc"])
    def test_semver_fail(self, proj: Path, version: str):
        write_manifest(proj, _manifest({"v": version}, {"v": "semver"}))
        result = run_align("lock", project_dir=proj)
        assert result.exit_code == 1

    def test_semver_rejects_int(self, proj: Path):
        write_manifest(proj, _manifest({"v": 3}, {"v": "semver"}))
        result = run_align("lock", project_dir=proj)
        assert result.exit_code == 1


class TestMalformedTypeSpec:
    def test_unknown_type_is_error(self, proj: Path):
        write_manifest(proj, _manifest({"x": "v"}, {"x": "uuid"}))
        result = run_align("lock", project_dir=proj)
        assert result.exit_code == 1

    def test_property_in_types_but_not_properties(self, proj: Path):
        write_manifest(proj, _manifest({}, {"ghost": "string"}))
        result = run_align("lock", project_dir=proj)
        assert result.exit_code == 1


class TestUntypedFallback:
    def test_no_property_types_is_untyped(self, proj: Path):
        # No property_types declared → "3" doesn't error
        m = {
            "version": "1.0.0",
            "project": {"name": "t", "intent": "t"},
            "symbols": {
                "x": {"description": "x", "docs": [], "properties": {"n": "3"}, "interlocks": {}}
            },
        }
        write_manifest(proj, m)
        run_align("lock", project_dir=proj).assert_ok()

    def test_partial_typing_only_validates_declared(self, proj: Path):
        # Only `a` is typed; `b` is untyped and can be anything
        m = _manifest({"a": "x", "b": [1, 2, 3]}, {"a": "string"})
        write_manifest(proj, m)
        run_align("lock", project_dir=proj).assert_ok()


class TestCheckExitCode:
    def test_check_returns_1_on_type_error(self, proj: Path):
        # Initial: type-clean
        write_manifest(proj, _manifest({"n": 3}, {"n": "int"}))
        run_align("lock", project_dir=proj).assert_ok()
        # Now corrupt
        write_manifest(proj, _manifest({"n": "3"}, {"n": "int"}))
        result = run_align("check", project_dir=proj)
        assert result.exit_code == 1
        assert "Type error" in result.stdout
