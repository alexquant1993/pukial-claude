"""T2.1 ARB parity: the sweep compares the languages the app actually has."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

SKILL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL))

import sweep  # noqa: E402


def write_arb(directory, lang, keys, metadata=True):
    directory.mkdir(parents=True, exist_ok=True)
    body = {"@@locale": lang}
    for k in keys:
        body[k] = f"{k} ({lang})"
        if metadata:
            body[f"@{k}"] = {"description": f"about {k}"}
    (directory / f"app_{lang}.arb").write_text(json.dumps(body, indent=2), encoding="utf-8")


def messages(findings):
    return sorted(f["message"] for f in findings)


def test_one_language_passes_silently(tmp_path):
    write_arb(tmp_path / "lib/l10n", "en", ["a", "b"])
    findings, info = sweep.check_arb_parity(tmp_path)
    assert findings == []
    assert info["compared"] is False
    assert info["languages"] == ["en"]


def test_frozen_copy_elsewhere_is_not_counted(tmp_path):
    write_arb(tmp_path / "lib/l10n", "en", ["a"])
    write_arb(tmp_path / "docs/references/l10n", "es", ["a", "zzz"])
    findings, info = sweep.check_arb_parity(tmp_path)
    assert findings == []
    assert info["languages"] == ["en"]


def test_no_l10n_folder_is_silent(tmp_path):
    findings, info = sweep.check_arb_parity(tmp_path)
    assert findings == []
    assert info["compared"] is False


def test_two_matching_languages_pass_and_are_named(tmp_path):
    write_arb(tmp_path / "lib/l10n", "en", ["a", "b"])
    write_arb(tmp_path / "lib/l10n", "es", ["a", "b"], metadata=False)
    findings, info = sweep.check_arb_parity(tmp_path)
    assert findings == []
    assert info["compared"] is True
    assert info["languages"] == ["en", "es"]


def test_missing_key_is_reported(tmp_path):
    write_arb(tmp_path / "lib/l10n", "en", ["a", "b"])
    write_arb(tmp_path / "lib/l10n", "es", ["a"])
    findings, _ = sweep.check_arb_parity(tmp_path)
    assert len(findings) == 1
    assert "'b'" in findings[0]["message"] and "missing from app_es.arb" in findings[0]["message"]
    assert findings[0]["severity"] == "minor"
    assert findings[0]["file"] == "lib/l10n/app_en.arb"
    assert findings[0]["line"] > 1  # points at the key in the template


def test_five_languages_one_extra_key(tmp_path):
    keys = ["a", "b", "c"]
    for lang in ("en", "es", "fr", "nl"):
        write_arb(tmp_path / "lib/l10n", lang, keys)
    write_arb(tmp_path / "lib/l10n", "de", keys + ["stray"])
    findings, info = sweep.check_arb_parity(tmp_path)
    assert info["languages"] == ["en", "de", "es", "fr", "nl"]
    assert len(findings) == 1
    assert "'stray'" in findings[0]["message"] and "not in the template" in findings[0]["message"]
    assert findings[0]["file"] == "lib/l10n/app_de.arb"


def test_metadata_keys_do_not_count(tmp_path):
    write_arb(tmp_path / "lib/l10n", "en", ["a"], metadata=True)
    write_arb(tmp_path / "lib/l10n", "es", ["a"], metadata=False)
    findings, _ = sweep.check_arb_parity(tmp_path)
    assert findings == []


def test_custom_arb_dir_and_template_from_l10n_yaml(tmp_path):
    (tmp_path / "l10n.yaml").write_text(
        "# config\narb-dir: 'assets/i18n'  # custom\ntemplate-arb-file: app_de.arb\n",
        encoding="utf-8",
    )
    write_arb(tmp_path / "assets/i18n", "de", ["a", "b"])
    write_arb(tmp_path / "assets/i18n", "fr", ["a"])
    # A decoy in the default folder must be ignored.
    write_arb(tmp_path / "lib/l10n", "en", ["a", "b", "c"])
    write_arb(tmp_path / "lib/l10n", "es", ["a"])
    findings, info = sweep.check_arb_parity(tmp_path)
    assert info["arb_dir"] == "assets/i18n"
    assert info["languages"] == ["de", "fr"]
    assert len(findings) == 1 and "missing from app_fr.arb" in findings[0]["message"]


def test_invalid_json_is_a_finding_not_a_crash(tmp_path):
    write_arb(tmp_path / "lib/l10n", "en", ["a"])
    (tmp_path / "lib/l10n/app_es.arb").write_text("{ nope", encoding="utf-8")
    findings, _ = sweep.check_arb_parity(tmp_path)
    assert len(findings) == 1 and "not valid JSON" in findings[0]["message"]


def run_sweep(root):
    out = subprocess.run(
        [sys.executable, str(SKILL / "sweep.py"), "--root", str(root), "--format", "json"],
        capture_output=True, text=True, check=True,
    )
    return json.loads(out.stdout)


def test_cli_single_language_is_clean(tmp_path):
    write_arb(tmp_path / "lib/l10n", "en", ["a"])
    rep = run_sweep(tmp_path)
    assert rep["passed"] and rep["counts"]["in_diff"] == 0 and rep["counts"]["pre_existing"] == 0
    human = subprocess.run(
        [sys.executable, str(SKILL / "sweep.py"), "--root", str(tmp_path)],
        capture_output=True, text=True,
    ).stdout
    assert "ARB" not in human


def test_cli_names_languages_and_reports_gap(tmp_path):
    write_arb(tmp_path / "lib/l10n", "en", ["a", "b"])
    write_arb(tmp_path / "lib/l10n", "es", ["a"])
    rep = run_sweep(tmp_path)
    assert rep["passed"]  # minor never blocks
    assert rep["l10n"]["languages"] == ["en", "es"]
    assert rep["counts"]["in_diff"] + rep["counts"]["pre_existing"] == 1
    human = subprocess.run(
        [sys.executable, str(SKILL / "sweep.py"), "--root", str(tmp_path)],
        capture_output=True, text=True,
    ).stdout
    assert "ARB languages    : en, es" in human
