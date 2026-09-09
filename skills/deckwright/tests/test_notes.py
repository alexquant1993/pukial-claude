"""notes.py - every test reopens the saved package; nothing here reads source."""

import zipfile

import pytest
from pptx import Presentation
from pptx.enum.shapes import PP_PLACEHOLDER

from deck_kit import notes as notes_mod
from deck_kit.brand import load_brand
from deck_kit.deck import add_slide, open_deck
from deck_kit.notes import NOTES_MODES, Note, emit_notes, paragraphs, read_notes, write_notes
from deck_kit.notes import numbering, teleprompter_html, templates_dir
from deck_kit.primitives import textbox


@pytest.fixture(scope="module")
def brand():
    return load_brand("relay")


def _two_slide_deck(template, brand):
    prs = open_deck(template, brand)
    style = brand.style()
    for text in ("Slide one title", "Slide two title"):
        slide = add_slide(prs, brand)
        textbox(slide, 80, 80, 600, 40, text, 14, style.GREY, brand.sans)
    return prs


def test_paragraphs_split_on_blank_lines_and_drop_empties():
    assert paragraphs("first\n\n\n  second  \n\n") == ["first", "second"]


def test_write_notes_lands_paragraphs_in_the_notes_body_of_the_saved_package(tmp_path, template, brand):
    prs = _two_slide_deck(template, brand)
    written = write_notes(prs, [
        Note(1, "Cover", "Welcome.\n\nSecond paragraph.", minutes=1),
        Note(2, "Body", "> Only if asked: an aside.", minutes=2),
    ], font=brand.sans, size_pt=12, gap_pt=6)
    assert written == [1, 2]
    out = tmp_path / "notes.pptx"
    prs.save(str(out))

    with zipfile.ZipFile(out) as z:
        names = [n for n in z.namelist() if n.startswith("ppt/notesSlides/notesSlide")
                 and n.endswith(".xml")]
        assert len(names) == 2
        bodies = [z.read(n).decode("utf-8") for n in names]
    joined = "\n".join(bodies)
    assert "Welcome." in joined and "Second paragraph." in joined
    assert "Only if asked: an aside." in joined
    assert 'type="body"' in joined, "the text did not land in a BODY placeholder"

    got = read_notes(Presentation(str(out)))
    assert got == {1: ["Welcome.", "Second paragraph."], 2: ["> Only if asked: an aside."]}


def test_write_notes_sets_the_font_and_size_on_every_run(tmp_path, template, brand):
    prs = _two_slide_deck(template, brand)
    write_notes(prs, [Note(1, "a", "x"), Note(2, "b", "y\n\nz")], font=brand.sans, size_pt=11,
                gap_pt=6)
    out = tmp_path / "font.pptx"
    prs.save(str(out))
    with zipfile.ZipFile(out) as z:
        body = z.read("ppt/notesSlides/notesSlide2.xml").decode("utf-8")
    assert body.count('sz="1100"') == 2, body
    assert body.count('typeface="%s"' % brand.sans) == 2
    assert body.count('<a:spcBef><a:spcPts val="600"/></a:spcBef>') == 1, body


def test_write_notes_refuses_a_note_list_that_does_not_cover_every_slide(template, brand):
    prs = _two_slide_deck(template, brand)
    with pytest.raises(ValueError, match="missing.*2"):
        write_notes(prs, [Note(1, "a", "x")], font=brand.sans, size_pt=12, gap_pt=6)
    with pytest.raises(ValueError, match="duplicate.*1"):
        write_notes(prs, [Note(1, "a", "x"), Note(1, "b", "y")], font=brand.sans,
                    size_pt=12, gap_pt=6)
    with pytest.raises(ValueError, match="outside"):
        write_notes(prs, [Note(1, "a", "x"), Note(2, "b", "y"), Note(3, "c", "z")],
                    font=brand.sans, size_pt=12, gap_pt=6)


def test_write_notes_reaches_ensure_notes_body_when_the_master_has_no_body(tmp_path, template, brand):
    """Catalogue item 11, consumed rather than reimplemented: with the notes
    master's BODY placeholder stripped and one slide's own notes body
    stripped, the only way the note can land is through
    textedit.ensure_notes_body's donor clone. A write_notes that touched
    notes_text_frame directly would silently write nothing here."""
    prs = _two_slide_deck(template, brand)
    donor, target = prs.slides[0], prs.slides[1]
    donor.notes_slide.notes_text_frame.text = "seed"
    target.notes_slide

    def _strip_body(shapes):
        for shape in list(shapes):
            if shape.is_placeholder and shape.placeholder_format.type == PP_PLACEHOLDER.BODY:
                shape._element.getparent().remove(shape._element)

    _strip_body(prs.notes_master.placeholders)
    _strip_body(target.notes_slide.shapes)
    assert target.notes_slide.notes_text_frame is None, "fixture did not strip the target"

    write_notes(prs, [Note(1, "a", "donor text"), Note(2, "b", "target text")],
                font=brand.sans, size_pt=12, gap_pt=6)
    out = tmp_path / "clone.pptx"
    prs.save(str(out))
    got = read_notes(Presentation(str(out)))
    assert got[2] == ["target text"]
    assert got[1] == ["donor text"]


def test_read_notes_omits_slides_that_have_no_notes(tmp_path, template, brand):
    prs = _two_slide_deck(template, brand)
    prs.slides[0].notes_slide.notes_text_frame.text = "only the first"
    out = tmp_path / "partial.pptx"
    prs.save(str(out))
    assert read_notes(Presentation(str(out))) == {1: ["only the first"]}


def test_numbering_reports_printed_numbers_and_hidden_flags(template, brand):
    """Structure of `numbering`'s output only. Agreement with `renumber` is
    pinned in tests/test_pagenums.py::test_renumber_report_agrees_with_visible_numbers,
    which calls both mechanisms; asserting `numbering` against
    `visible_numbers` here would be a tautology, since one is built on the other."""
    prs = _two_slide_deck(template, brand)
    third = add_slide(prs, brand)
    textbox(third, 80, 80, 600, 40, "hidden", 14, brand.style().GREY, brand.sans)
    third._element.set("show", "0")
    assert numbering(prs, skip=(1,)) == {1: (None, False), 2: (2, False), 3: (None, True)}


def test_templates_dir_comes_from_the_environment_when_it_is_set(tmp_path, monkeypatch):
    monkeypatch.setenv("DECKWRIGHT_TEMPLATES", str(tmp_path))
    assert templates_dir() == tmp_path
    monkeypatch.delenv("DECKWRIGHT_TEMPLATES")
    assert (templates_dir() / "teleprompter.html").exists()


def test_teleprompter_has_one_section_per_note_with_printed_numbers_and_hidden_flags(tmp_path):
    notes = [
        Note(1, "Cover", "Welcome & thanks.", minutes=1),
        Note(2, "Body", "Main point.\n\n> Only if asked.", minutes=3),
        Note(3, "Backup", "Hidden slide.", minutes=0, section="Annex"),
    ]
    numbering_ = {1: (None, False), 2: (2, False), 3: (None, True)}
    html_text = teleprompter_html(notes, numbering_, title="Walkthrough <deck>")
    out = tmp_path / "t.html"
    out.write_text(html_text, encoding="utf-8")
    got = out.read_text(encoding="utf-8")

    assert got.count('<section id="s') == 3
    assert '<section id="s1"' in got and '<section id="s2"' in got and '<section id="s3"' in got
    assert "Welcome &amp; thanks." in got, "text is not HTML-escaped"
    assert "Walkthrough &lt;deck&gt;" in got, "title is not HTML-escaped"
    assert "Slide 2 [2]" in got, "printed number missing from the slide label"
    assert "Slide 3 · hidden" in got, "hidden flag missing"
    assert "Slide 1 [" not in got, "the cover must not show a printed number"
    assert 'class="aside"' in got and "Only if asked." in got
    assert "Annex" in got
    assert "4 min" in got, "total minutes missing (1 + 3 + 0)"
    assert '<a href="#s2">' in got, "nav pill missing"
    assert "{{" not in got, "an unfilled placeholder survived"


def test_teleprompter_refuses_notes_and_numbering_that_disagree():
    with pytest.raises(ValueError, match="numbering"):
        teleprompter_html([Note(1, "a", "x")], {1: (None, False), 2: (2, False)}, title="t")


def test_teleprompter_keeps_braces_in_note_text_and_never_substitutes_into_content():
    notes = [
        Note(1, "Cover", "Welcome.", minutes=1),
        Note(2, "Body", "See {{nav}} for reference.", minutes=2),
        Note(3, "Backup", "Hidden slide.", minutes=0),
    ]
    numbering_ = {1: (None, False), 2: (2, False), 3: (None, True)}
    got = teleprompter_html(notes, numbering_, title="Walkthrough {{title}}")
    assert "See {{nav}} for reference." in got
    assert "Walkthrough {{title}}" in got
    assert got.count("<section id=\"s") == 3


def test_teleprompter_refuses_a_template_with_an_unknown_or_missing_placeholder(tmp_path):
    bad = tmp_path / "bad.html"
    bad.write_text("<html>{{title}}{{total_minutes}}{{nav}}{{bogus}}</html>", encoding="utf-8")
    with pytest.raises(ValueError, match="bogus"):
        teleprompter_html([Note(1, "a", "x")], {1: (None, False)}, title="t", template=bad)


# ---- emit_notes: the opt-in entry point ------------------------------------

_TWO_NOTES = [Note(1, "Cover", "Welcome.", minutes=1),
              Note(2, "Body", "Main point.\n\n> Only if asked.", minutes=2)]


def _emit(prs, mode, brand, tmp_path, teleprompter="t.html"):
    return emit_notes(prs, _TWO_NOTES, mode, font=brand.sans, size_pt=12, gap_pt=6,
                      title="Walkthrough",
                      teleprompter=tmp_path / teleprompter if teleprompter else None)


def test_notes_modes_are_the_four_the_builders_offer():
    assert NOTES_MODES == ("none", "pptx", "teleprompter", "both")


def test_emit_notes_none_writes_nothing_to_the_package_or_the_disk(tmp_path, template, brand):
    """The default for every deck. Reopens the saved package: a notes slide
    that write_notes never touched must not exist there either."""
    prs = _two_slide_deck(template, brand)
    emitted = _emit(prs, "none", brand, tmp_path)
    assert emitted == {"pptx": None, "teleprompter": None}
    out = tmp_path / "none.pptx"
    prs.save(str(out))
    with zipfile.ZipFile(out) as z:
        assert not [n for n in z.namelist() if n.startswith("ppt/notesSlides/notesSlide")]
    assert read_notes(Presentation(str(out))) == {}
    assert not (tmp_path / "t.html").exists()


def test_emit_notes_none_does_not_validate_coverage(template, brand):
    """A note list nobody asked to emit cannot fail the build - one note for
    two slides is a write_notes error, and "none" never reaches it."""
    prs = _two_slide_deck(template, brand)
    emitted = emit_notes(prs, [Note(1, "a", "x")], "none", font=brand.sans, size_pt=12,
                         gap_pt=6, title="t")
    assert emitted == {"pptx": None, "teleprompter": None}


def test_emit_notes_pptx_writes_the_pane_only(tmp_path, template, brand):
    prs = _two_slide_deck(template, brand)
    emitted = _emit(prs, "pptx", brand, tmp_path)
    assert emitted == {"pptx": [1, 2], "teleprompter": None}
    out = tmp_path / "pptx.pptx"
    prs.save(str(out))
    assert read_notes(Presentation(str(out))) == {1: ["Welcome."],
                                                  2: ["Main point.", "> Only if asked."]}
    assert not (tmp_path / "t.html").exists()


def test_emit_notes_teleprompter_writes_the_page_only(tmp_path, template, brand):
    prs = _two_slide_deck(template, brand)
    emitted = _emit(prs, "teleprompter", brand, tmp_path, teleprompter="deep/dir/t.html")
    page = tmp_path / "deep" / "dir" / "t.html"
    assert emitted == {"pptx": None, "teleprompter": page}
    got = page.read_text(encoding="utf-8")
    assert got.count('<section id="s') == 2 and "Slide 2 [2]" in got
    assert "Slide 1 [" not in got, "the cover must not show a printed number"
    out = tmp_path / "tele.pptx"
    prs.save(str(out))
    assert read_notes(Presentation(str(out))) == {}


def test_emit_notes_both_writes_the_pane_and_the_page(tmp_path, template, brand):
    prs = _two_slide_deck(template, brand)
    emitted = _emit(prs, "both", brand, tmp_path)
    assert emitted == {"pptx": [1, 2], "teleprompter": tmp_path / "t.html"}
    out = tmp_path / "both.pptx"
    prs.save(str(out))
    assert read_notes(Presentation(str(out))) == {1: ["Welcome."],
                                                  2: ["Main point.", "> Only if asked."]}
    assert '<section id="s2"' in (tmp_path / "t.html").read_text(encoding="utf-8")


def test_emit_notes_refuses_an_unknown_mode_naming_the_modes(template, brand):
    prs = _two_slide_deck(template, brand)
    with pytest.raises(ValueError, match="none, pptx, teleprompter, both"):
        emit_notes(prs, _TWO_NOTES, "all", font=brand.sans, size_pt=12, gap_pt=6, title="t")


@pytest.mark.parametrize("mode", ["teleprompter", "both"])
def test_emit_notes_refuses_a_teleprompter_mode_without_a_path(tmp_path, template, brand, mode):
    prs = _two_slide_deck(template, brand)
    with pytest.raises(ValueError, match="teleprompter.*path"):
        _emit(prs, mode, brand, tmp_path, teleprompter=None)
    out = tmp_path / "refused.pptx"
    prs.save(str(out))
    assert read_notes(Presentation(str(out))) == {}, "the refusal must come before any write"
