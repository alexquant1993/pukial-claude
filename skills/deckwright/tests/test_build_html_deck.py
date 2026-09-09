"""build_html_deck.py - the HTML deliverable, when the spec's Output line says so.

The stage page is the deck, not a preview of one: it is what gets sent, and
what gets printed to PDF. So the things asserted here are the things a
reader would notice were wrong - the slides in the wrong order, a counter
that does not count, a stylesheet fetched from a CDN that is not there on
the aeroplane, and a print stylesheet that puts two slides on one page.
"""

import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_html_deck.py"
sys.path.insert(0, str(ROOT / "scripts"))

import build_html_deck as bhd  # noqa: E402

HORIZON = ROOT / "examples" / "ai-horizon" / "drafts"


def _draft(directory, name, body, head=""):
    directory.mkdir(parents=True, exist_ok=True)
    (directory / name).write_text(
        '<!doctype html>\n<!-- DISPOSABLE -->\n<html lang="en"><head>'
        '<meta charset="utf-8"><title>%s</title>%s</head>'
        '<body>\n<div class="slide">%s</div>\n</body></html>'
        % (name.split("-", 1)[-1].replace(".html", ""), head, body),
        encoding="utf-8")
    return directory / name


@pytest.fixture
def drafts(tmp_path):
    d = tmp_path / "drafts"
    _draft(d, "s01-cover.html", "<h1>Cover</h1>",
           head='<link rel="stylesheet" href="../css/slide.css">')
    _draft(d, "s02-body.html", "<p>Body</p>",
           head='<link rel="stylesheet" href="../css/slide.css">')
    _draft(d, "s10-last.html", "<p>Last</p>",
           head='<link rel="stylesheet" href="../css/slide.css">')
    (tmp_path / "css").mkdir()
    (tmp_path / "css" / "slide.css").write_text(".slide{}", encoding="utf-8")
    return d


def test_the_slides_come_out_in_numeric_order_not_lexical(drafts, tmp_path):
    """`s10-last.html` sorts before `s02-body.html` as a string. A deck in
    the wrong order is one nobody notices is wrong until the meeting."""
    assert [p.name for p in bhd.slide_files(drafts)] == [
        "s01-cover.html", "s02-body.html", "s10-last.html"]
    page = bhd.build_page(drafts, tmp_path / "html")
    order = re.findall(r'data-title="([^"]+)"', page)
    assert order == ["cover", "body", "last"]
    assert page.index("Cover") < page.index("Body") < page.index("Last")


def test_two_drafts_claiming_one_number_are_refused(drafts):
    _draft(drafts, "s02-other.html", "<p>Other</p>")
    with pytest.raises(bhd.DraftError, match="claim slide 2"):
        bhd.slide_files(drafts)


def test_a_drafts_directory_with_no_slides_is_refused(tmp_path):
    (tmp_path / "empty").mkdir()
    with pytest.raises(bhd.DraftError, match="no sNN"):
        bhd.slide_files(tmp_path / "empty")


def test_the_counter_counts_every_slide_and_starts_at_one(drafts, tmp_path):
    page = bhd.build_page(drafts, tmp_path / "html")
    assert '<span id="dw-counter">1 / 3</span>' in page
    assert page.count('class="dw-slide"') == 3
    # Exactly one slide visible on load; the rest carry `hidden`.
    assert page.count(' hidden>') == 2


def test_the_page_navigates_by_key_and_by_click(drafts, tmp_path):
    page = bhd.build_page(drafts, tmp_path / "html")
    for key in ("ArrowLeft", "ArrowRight", "Home", "End"):
        assert "'%s'" % key in page, key
    assert "addEventListener('keydown'" in page
    assert "viewport.addEventListener('click'" in page
    assert 'id="dw-prev"' in page and 'id="dw-next"' in page


def test_the_page_carries_a_print_rule_of_one_slide_per_landscape_page(drafts, tmp_path):
    page = bhd.build_page(drafts, tmp_path / "html")
    assert "@media print" in page
    # 13.333in x 7.5in is 1280x720 CSS px at 96dpi, wider than it is tall,
    # which is what makes the sheet landscape without an orientation keyword.
    assert "@page { size: 13.333in 7.5in; margin: 0 }" in page
    assert "page-break-after: always" in page
    # Every slide is shown when printing; the stage hides all but one.
    assert ".dw-slide, .dw-slide[hidden] {" in page


def test_no_external_network_resource_reaches_the_page(drafts, tmp_path):
    page = bhd.build_page(drafts, tmp_path / "html")
    assert not re.search(r'(?:src|href)="(?:https?:)?//', page)
    assert "cdn" not in page.lower()


def test_a_draft_that_links_a_remote_resource_is_refused(drafts, tmp_path):
    _draft(drafts, "s03-remote.html", "<p>x</p>",
           head='<link rel="stylesheet" href="https://fonts.example/x.css">')
    with pytest.raises(bhd.DraftError, match="no external network resource"):
        bhd.build_page(drafts, tmp_path / "html")


def test_a_protocol_relative_url_is_refused_too(drafts, tmp_path):
    _draft(drafts, "s04-proto.html", '<img src="//cdn.example/logo.png">')
    with pytest.raises(bhd.DraftError, match="no external network resource"):
        bhd.build_page(drafts, tmp_path / "html")


def test_a_draft_carrying_a_script_is_refused(drafts, tmp_path):
    _draft(drafts, "s05-script.html", "<p>x</p><script>alert(1)</script>")
    with pytest.raises(bhd.DraftError, match="<script>"):
        bhd.build_page(drafts, tmp_path / "html")


def test_relative_links_are_rewritten_from_the_output_directory(drafts, tmp_path):
    """The stage page lives somewhere else, so a draft's own
    `../css/slide.css` means nothing from there."""
    page = bhd.build_page(drafts, tmp_path / "out" / "deep" / "html")
    assert '<link rel="stylesheet" href="../../../css/slide.css">' in page
    assert page.count('href="../../../css/slide.css"') == 1, \
        "one stylesheet, linked once, however many drafts share it"


def test_an_image_src_is_rewritten_too(drafts, tmp_path):
    _draft(drafts, "s03-img.html", '<img src="../img/mark.png" alt="Mark">')
    page = bhd.build_page(drafts, tmp_path / "html")
    assert '<img src="../img/mark.png" alt="Mark">' in page
    assert "</img>" not in page, "img is a void element"


def test_the_drafts_own_comments_do_not_travel_into_the_deliverable(drafts, tmp_path):
    page = bhd.build_page(drafts, tmp_path / "html")
    assert "DISPOSABLE" not in page


def test_expect_slides_is_exact(drafts, tmp_path):
    with pytest.raises(bhd.DraftError, match="expected 4 slide"):
        bhd.build(drafts, tmp_path / "html", expect_slides=4)
    index, count = bhd.build(drafts, tmp_path / "html", expect_slides=3)
    assert count == 3 and index.read_text(encoding="utf-8").startswith("<!doctype html>")


def test_the_cli_writes_index_html_and_reports_the_count(drafts, tmp_path):
    out = tmp_path / "html"
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--drafts", str(drafts), "--out", str(out),
         "--title", "A deck", "--expect-slides", "3"],
        capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "3 slide(s)" in proc.stdout
    assert (out / "index.html").is_file()
    assert "<title>A deck</title>" in (out / "index.html").read_text(encoding="utf-8")


def test_the_cli_fails_cleanly_on_a_missing_drafts_directory(tmp_path):
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--drafts", str(tmp_path / "nope"),
         "--out", str(tmp_path / "html")],
        capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 1
    assert proc.stdout.startswith("FAIL:")
    assert "Traceback" not in proc.stdout + proc.stderr


# --- against the repository's own drafts ---------------------------------

def test_the_ai_horizon_drafts_build_a_ten_slide_stage_page(tmp_path):
    """The real thing: ten drafts written against brands/relay, linking that
    brand's slide.css and two committed PNGs."""
    page = bhd.build_page(HORIZON, tmp_path / "html")
    assert page.count('class="dw-slide"') == 10
    assert '<span id="dw-counter">1 / 10</span>' in page
    assert "1 / 10" in page
    # The brand stylesheet, resolved from the output directory and linked once.
    sheets = re.findall(r'<link rel="stylesheet" href="([^"]+)">', page)
    assert len(sheets) == 1
    assert (tmp_path / "html" / sheets[0]).resolve() == \
        (ROOT / "brands" / "relay" / "slide.css").resolve()
    assert not re.search(r'(?:src|href)="(?:https?:)?//', page)
    # Every image the page places resolves to a file that is committed.
    for src in re.findall(r'<img[^>]+src="([^"]+)"', page):
        assert (tmp_path / "html" / src).resolve().is_file(), src
