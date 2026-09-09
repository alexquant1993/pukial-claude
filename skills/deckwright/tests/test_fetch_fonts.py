"""scripts/fetch_fonts.py - never over the network.

`fetch_fonts.fetch_bytes` is the one function that opens a socket, and
every test here monkeypatches it. A test that actually downloaded would
pass on a machine with a warm proxy cache and fail in CI for reasons that
have nothing to do with the fetcher, and would take the repository's only
network dependency into the unit suite.
"""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import fetch_fonts  # noqa: E402

REGULAR = b"regular face bytes"
BOLD = b"bold face bytes"
LICENCE = b"SIL OPEN FONT LICENSE Version 1.1 ...\n"

REGULAR_SHA = fetch_fonts.sha256(REGULAR)
BOLD_SHA = fetch_fonts.sha256(BOLD)

BASE = "https://example.invalid/"
BODY = {BASE + "Regular.ttf": REGULAR, BASE + "Bold.ttf": BOLD,
        BASE + "OFL.txt": LICENCE}


@pytest.fixture
def served(monkeypatch):
    """A recording stand-in for the download. Returns the URL list."""
    calls = []

    def fake(url):
        calls.append(url)
        if url not in BODY:
            raise AssertionError("unexpected url: %s" % url)
        return BODY[url]

    monkeypatch.setattr(fetch_fonts, "fetch_bytes", fake)
    return calls


def _entry(**over):
    entry = {
        "family": "Example Face",
        "role": "sans",
        "weight": "regular",
        "file": "Regular.ttf",
        "url": BASE + "Regular.ttf",
        "sha256": "",
        "licence": fetch_fonts.OFL,
        "licence_url": BASE + "OFL.txt",
        "licence_file": "OFL.txt",
    }
    entry.update(over)
    return entry


def _toml(entries):
    out = []
    for e in entries:
        out.append("[[font]]")
        out += ['%s = "%s"' % (k, v) for k, v in e.items()]
        out.append("")
    return "\n".join(out)


def _brand(tmp_path, entries, name="fake"):
    d = tmp_path / name
    (d / "fonts").mkdir(parents=True)
    (d / "fonts.toml").write_text(_toml(entries), encoding="utf-8")
    return d


# --- the manifest -----------------------------------------------------------

def test_a_brand_with_no_manifest_declares_no_fonts(tmp_path):
    (tmp_path / "bare").mkdir()
    assert fetch_fonts.read_manifest(tmp_path / "bare") == []


def test_a_non_ofl_licence_is_refused(tmp_path):
    d = _brand(tmp_path, [_entry(licence="All rights reserved")])
    with pytest.raises(fetch_fonts.ManifestError, match="only .* may be fetched"):
        fetch_fonts.read_manifest(d)


def test_a_role_outside_the_three_is_refused(tmp_path):
    d = _brand(tmp_path, [_entry(role="handwriting")])
    with pytest.raises(fetch_fonts.ManifestError, match="role"):
        fetch_fonts.read_manifest(d)


def test_a_file_with_a_path_separator_is_refused(tmp_path):
    """A destination is a bare filename inside fonts/. '../../example/...'
    is a manifest that overwrites another brand's faces."""
    d = _brand(tmp_path, [_entry(file="../../example/fonts/NotoSans-Regular.ttf")])
    with pytest.raises(fetch_fonts.ManifestError, match="bare filename"):
        fetch_fonts.read_manifest(d)


def test_a_plain_http_url_is_refused(tmp_path):
    d = _brand(tmp_path, [_entry(url="http://example.invalid/Regular.ttf")])
    with pytest.raises(fetch_fonts.ManifestError, match="https"):
        fetch_fonts.read_manifest(d)


def test_the_same_file_declared_twice_is_refused(tmp_path):
    d = _brand(tmp_path, [_entry(), _entry(weight="bold")])
    with pytest.raises(fetch_fonts.ManifestError, match="declared twice"):
        fetch_fonts.read_manifest(d)


def test_a_short_digest_is_refused(tmp_path):
    d = _brand(tmp_path, [_entry(sha256="abc123")])
    with pytest.raises(fetch_fonts.ManifestError, match="64-character"):
        fetch_fonts.read_manifest(d)


# --- fetching ---------------------------------------------------------------

def test_the_first_fetch_writes_the_face_and_its_licence(tmp_path, served, capsys):
    d = _brand(tmp_path, [_entry()])
    code = fetch_fonts.run(d)
    assert (d / "fonts" / "Regular.ttf").read_bytes() == REGULAR
    assert (d / "fonts" / "OFL.txt").read_bytes() == LICENCE
    out = capsys.readouterr().out
    assert REGULAR_SHA in out, "the hash a human has to pin is never printed"
    # Unpinned is not ready: exit 1 until somebody writes the hash down.
    assert code == 1


def test_a_pinned_face_already_on_disk_is_not_downloaded(tmp_path, served):
    d = _brand(tmp_path, [_entry(sha256=REGULAR_SHA)])
    (d / "fonts" / "Regular.ttf").write_bytes(REGULAR)
    assert fetch_fonts.run(d) == 0
    assert served == [], "a matching face must not be re-downloaded"


def test_a_pinned_face_on_disk_is_not_rewritten(tmp_path, served):
    """Not merely 'not downloaded': the bytes on disk are left alone, so a
    re-run cannot change a file's mtime and make a clean tree look dirty."""
    d = _brand(tmp_path, [_entry(sha256=REGULAR_SHA)])
    face = d / "fonts" / "Regular.ttf"
    face.write_bytes(REGULAR)
    before = face.stat().st_mtime_ns
    fetch_fonts.run(d)
    assert face.stat().st_mtime_ns == before


def test_a_face_whose_bytes_moved_is_refused_not_overwritten(tmp_path, served):
    d = _brand(tmp_path, [_entry(sha256=REGULAR_SHA)])
    face = d / "fonts" / "Regular.ttf"
    face.write_bytes(b"something else entirely")
    with pytest.raises(fetch_fonts.FetchRefused, match="refusing to overwrite"):
        fetch_fonts.run(d)
    assert face.read_bytes() == b"something else entirely"
    assert served == []


def test_a_download_that_does_not_match_the_pin_writes_nothing(tmp_path, served):
    """The pin is checked BEFORE the write. A fetcher that wrote first and
    verified second would leave the wrong bytes on disk on every failure."""
    d = _brand(tmp_path, [_entry(sha256=BOLD_SHA)])   # pins the wrong hash
    with pytest.raises(fetch_fonts.FetchRefused, match="nothing written"):
        fetch_fonts.run(d)
    assert not (d / "fonts" / "Regular.ttf").exists()
    assert not (d / "fonts" / "OFL.txt").exists()


def test_a_missing_pinned_face_is_fetched_and_verified(tmp_path, served):
    d = _brand(tmp_path, [_entry(sha256=REGULAR_SHA)])
    assert fetch_fonts.run(d) == 0
    assert (d / "fonts" / "Regular.ttf").read_bytes() == REGULAR
    assert served == [BASE + "Regular.ttf", BASE + "OFL.txt"]


def test_dry_run_touches_neither_the_network_nor_the_disk(tmp_path, served):
    d = _brand(tmp_path, [_entry(sha256=REGULAR_SHA)])
    assert fetch_fonts.run(d, dry_run=True) == 1
    assert served == []
    assert not (d / "fonts" / "Regular.ttf").exists()


def test_check_reports_without_fetching(tmp_path, served, capsys):
    d = _brand(tmp_path, [_entry(sha256=REGULAR_SHA),
                          _entry(weight="bold", file="Bold.ttf",
                                 url=BASE + "Bold.ttf", sha256=BOLD_SHA)])
    (d / "fonts" / "Regular.ttf").write_bytes(REGULAR)
    assert fetch_fonts.run(d, check=True) == 1
    out = capsys.readouterr().out
    assert "ok        Regular.ttf" in out
    assert "missing   Bold.ttf" in out
    assert served == []


# --- what discover.py asks --------------------------------------------------

def test_missing_fonts_lists_the_faces_not_on_disk(tmp_path):
    d = _brand(tmp_path, [_entry(sha256=REGULAR_SHA),
                          _entry(weight="bold", file="Bold.ttf",
                                 url=BASE + "Bold.ttf", sha256=BOLD_SHA)])
    (d / "fonts" / "Regular.ttf").write_bytes(REGULAR)
    assert fetch_fonts.missing_fonts(d) == [("Example Face", "bold", "Bold.ttf")]


def test_missing_fonts_reports_a_broken_manifest_rather_than_raising(tmp_path):
    """The intake report calls this for every brand. A brand with a typo in
    its fonts.toml must show up as a line in the report, not as a traceback
    that stops the whole intake."""
    d = _brand(tmp_path, [_entry(licence="Proprietary")])
    (found,) = fetch_fonts.missing_fonts(d)
    assert found[0].startswith("fonts.toml:")


# --- the real brand ---------------------------------------------------------

def test_the_relay_brand_declares_six_ofl_faces_and_has_them_all():
    """The one test that reads the repository rather than a fixture: this is
    what keeps `brands/relay`'s manifest and its fonts/ directory honest
    without the gate having to reach the network."""
    entries = fetch_fonts.read_manifest(ROOT / "brands" / "relay")
    assert len(entries) == 6, [e["file"] for e in entries]
    assert {e["role"] for e in entries} == {"display", "sans", "mono"}
    assert all(e["licence"] == fetch_fonts.OFL for e in entries)
    assert all(e["sha256"] for e in entries), "every face is pinned"
    assert fetch_fonts.missing_fonts(ROOT / "brands" / "relay") == []
    for entry in entries:
        assert fetch_fonts.face_status(ROOT / "brands" / "relay", entry) == "ok"
        assert (ROOT / "brands" / "relay" / "fonts" / entry["licence_file"]).is_file()
