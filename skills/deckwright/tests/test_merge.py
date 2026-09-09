"""Every test here opens the built package and reads its XML.

A source grep cannot see a re-minted id, a dropped relationship or the order
of entries in a zip. Phase 1 shipped two false doctrines because its tests
grepped; none of these do.
"""

import re
import zipfile

import pytest
from pptx import Presentation

from deck_kit import merge
from deck_kit.brand import load_brand
from deck_kit.deck import add_slide, open_deck
from deck_kit.primitives import textbox

COMMENT_EXT_URI = "{6950BFC3-D8DA-4A85-94F7-54DA5524770B}"


@pytest.fixture(scope="module")
def brand():
    return load_brand("relay")


def _deck(path, template, brand, n, label):
    """A deck of n slides, each carrying one identifying text box."""
    prs = open_deck(template, brand)
    style = brand.style()
    for i in range(n):
        slide = add_slide(prs, brand)
        textbox(slide, 80, 80, 600, 40, "%s %d" % (label, i + 1),
                20, style.GREY, brand.sans)
    prs.save(str(path))
    return path


@pytest.fixture(scope="module")
def host(tmp_path_factory, template, brand):
    return _deck(tmp_path_factory.mktemp("m") / "host.pptx", template, brand, 3, "HOST")


@pytest.fixture(scope="module")
def donor(tmp_path_factory, template, brand):
    return _deck(tmp_path_factory.mktemp("m") / "donor.pptx", template, brand, 2, "DONOR")


@pytest.fixture(scope="module")
def merged(tmp_path_factory, host, donor):
    out = tmp_path_factory.mktemp("m") / "merged.pptx"
    merge.merge(host, donor, [(1, 2, False), (2, 5, True)], out, verbose=False)
    return out


def test_dangling_refs_is_empty_on_a_package_nobody_merged(template):
    """The checker's floor. A checker that fails on a valid file is worse
    than no checker, and this one gates six tests and a gate step."""
    assert merge.dangling_refs(merge.read_package(template)) == []


def test_slides_land_at_the_positions_asked_for(merged):
    prs = Presentation(str(merged))
    texts = [s.shapes[0].text_frame.text for s in prs.slides]
    assert texts == ["HOST 1", "DONOR 1", "HOST 2", "HOST 3", "DONOR 2"]


def test_content_types_is_the_first_entry_in_the_package(merged):
    """Catalogue item 3."""
    with zipfile.ZipFile(str(merged)) as z:
        assert z.namelist()[0] == "[Content_Types].xml"


def test_copied_master_layout_ids_do_not_collide_with_the_destination(merged):
    """Catalogue item 5. The re-minted p:sldLayoutId values live inside the
    copied master parts, not in ppt/presentation.xml - reading
    'presentation-scope' as 'in presentation.xml' misses the master rewrite."""
    parts = merge.read_package(merged)
    masters = [n for n in parts if re.match(r"ppt/slideMasters/slideMaster\d+\.xml$", n)]
    assert len(masters) == 2, "the donor's master should have been copied"
    seen = []
    for m in sorted(masters):
        ids = re.findall(r'<p:sldLayoutId id="(\d+)"', parts[m].decode("utf-8"))
        assert ids, "master %s declares no layout ids" % m
        seen.extend(int(i) for i in ids)
    assert len(seen) == len(set(seen)), "duplicate p:sldLayoutId across masters: %s" % seen
    pres = parts["ppt/presentation.xml"].decode("utf-8")
    master_ids = [int(i) for i in re.findall(r'<p:sldMasterId id="(\d+)"', pres)]
    assert len(master_ids) == len(set(master_ids)) == 2


def test_notes_and_comments_are_dropped_and_leave_no_dangling_rid(tmp_path, host, donor):
    """Catalogue item 6. The donor gets a notes slide and a modern-comment
    anchor; neither may survive, and neither may leave a reference behind."""
    prs = Presentation(str(donor))
    prs.slides[0].notes_slide.notes_text_frame.text = "donor note"
    doctored = tmp_path / "donor_with_notes.pptx"
    prs.save(str(doctored))
    assert [n for n in merge.read_package(doctored) if "notesSlide" in n]

    parts = merge.read_package(doctored)
    sld = merge.slide_order(parts)[0]
    xml = parts[sld].decode("utf-8")
    anchor = ('<p:extLst><p:ext uri="%s">'
              '<p188:commentRel xmlns:p188="http://example.invalid/p188" r:id="rId99"/>'
              "</p:ext></p:extLst>" % COMMENT_EXT_URI)
    parts[sld] = xml.replace("</p:sld>", anchor + "</p:sld>").encode("utf-8")
    merge.write_package(doctored, parts)

    out = tmp_path / "merged_notes.pptx"
    merge.merge(host, doctored, [(1, 1, False)], out, verbose=False)

    got = merge.read_package(out)
    assert not [n for n in got if "notesSlide" in n], "notes slide was copied"
    copied = merge.slide_order(got)[0]
    assert COMMENT_EXT_URI not in got[copied].decode("utf-8")
    assert merge.dangling_refs(got) == []


def test_hidden_flag_is_on_the_slide_root_not_on_sldId(merged):
    """Catalogue item 7. Verified empirically against PowerPoint COM."""
    parts = merge.read_package(merged)
    order = merge.slide_order(parts)
    root_tag = re.search(r"<p:sld(\s[^>]*?)?>", parts[order[4]].decode("utf-8")).group(0)
    assert 'show="0"' in root_tag
    pres = parts["ppt/presentation.xml"].decode("utf-8")
    assert 'show="0"' not in re.search(r"<p:sldIdLst>.*?</p:sldIdLst>", pres, re.S).group(0)
    for i, part in enumerate(order):
        if i == 4:
            continue
        tag = re.search(r"<p:sld(\s[^>]*?)?>", parts[part].decode("utf-8")).group(0)
        assert 'show="0"' not in tag


def test_the_merged_package_has_no_dangling_references(merged):
    assert merge.dangling_refs(merge.read_package(merged)) == []


def test_copied_parts_get_names_that_were_free(merged, host):
    """Part names must not collide, and must not silently overwrite a
    destination part that happened to have the same number."""
    before = set(merge.read_package(host))
    after = merge.read_package(merged)
    assert before <= set(after), "a destination part was overwritten"
    assert len(merge.slide_order(after)) == 5


def test_media_travels_with_the_slide(tmp_path, template, brand, host):
    """A picture on a donor slide must arrive with its media part and a
    relationship that resolves."""
    prs = open_deck(template, brand)
    slide = add_slide(prs, brand)
    slide.shapes.add_picture(str(brand.logo_primary), 100000, 100000)
    src = tmp_path / "pic.pptx"
    prs.save(str(src))

    out = tmp_path / "merged_pic.pptx"
    merge.merge(host, src, [(1, 1, False)], out, verbose=False)
    got = merge.read_package(out)
    assert len([n for n in got if n.startswith("ppt/media/")]) == 1
    assert merge.dangling_refs(got) == []


def test_merge_refuses_to_write_over_its_dest_or_src(tmp_path, host, donor):
    with pytest.raises(ValueError, match="overwrite"):
        merge.merge(host, donor, [(1, 1, False)], host, verbose=False)
    with pytest.raises(ValueError, match="overwrite"):
        merge.merge(host, donor, [(1, 1, False)], donor, verbose=False)


def test_merge_rejects_a_src_idx_out_of_range(tmp_path, host, donor):
    """src_idx=0 used to resolve src_order[-1] via Python's negative
    indexing and silently transplant the LAST donor slide instead of
    raising."""
    out = tmp_path / "bad.pptx"
    with pytest.raises(ValueError, match="src_idx"):
        merge.merge(host, donor, [(0, 1, False)], out, verbose=False)
    with pytest.raises(ValueError, match="src_idx"):
        merge.merge(host, donor, [(3, 1, False)], out, verbose=False)  # donor has 2


def test_merge_rejects_a_pos_out_of_range(tmp_path, host, donor):
    """pos=99 used to clamp silently to the end via list.insert."""
    out = tmp_path / "bad.pptx"
    with pytest.raises(ValueError, match="pos"):
        merge.merge(host, donor, [(1, 99, False)], out, verbose=False)
    with pytest.raises(ValueError, match="pos"):
        merge.merge(host, donor, [(1, 0, False)], out, verbose=False)


def test_merge_rejects_duplicate_positions(tmp_path, host, donor):
    """Two specs naming the same pos used to silently swap order instead of
    raising."""
    out = tmp_path / "bad.pptx"
    with pytest.raises(ValueError, match="duplicate"):
        merge.merge(host, donor, [(1, 2, False), (2, 2, False)], out, verbose=False)
