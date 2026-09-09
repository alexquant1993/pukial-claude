"""Page numbers.

Printed page number is not file position: covers are unnumbered, hidden
slides do not count, and the author reorders things. And the marker itself
comes in three incompatible flavours, which is catalogue item 14:

  1. a real slide-number placeholder whose paragraph holds an <a:fld
     type="slidenum">, with the run properties inside the field;
  2. an inherited text box named for the locale - "Numero de diapositiva",
     "Slide Number" - holding a literal;
  3. a plain literal text box on machine-built slides, recognised only by
     being small, low and numeric.

Renumbering has to handle all three, skip hidden slides in the visible count,
and preserve the run properties from inside a field when it replaces it.

The core holds no geometry and no colour, so `MarkerStyle` carries both and
the brand supplies them.
"""

import copy
from dataclasses import dataclass

from lxml import etree

from .geometry import px
from .primitives import textbox
from .textedit import iter_shapes

A = "http://schemas.openxmlformats.org/drawingml/2006/main"
P = "http://schemas.openxmlformats.org/presentationml/2006/main"
LOCALE_NAMES = ("mero de diapositiva", "Slide Number", "slidenum", "Page number")


def q(tag, ns=A):
    return "{%s}%s" % (ns, tag)


@dataclass
class MarkerStyle:
    x: int
    y: int
    w: int
    h: int
    size: float
    color: object
    font: str
    align: object = None


def _has_slidenum_field(shape):
    """A slidenum field specifically.

    Any <a:fld> is not enough: a date placeholder (type="datetime1") and a
    footer (type="ftr") are fields too, so a slide carrying a date above the
    page number would return the date box. renumber() then writes the page
    number into it and the deck ships with a number where the date was.
    """
    if not shape.has_text_frame:
        return False
    for fld in shape.text_frame._txBody.iter(q("fld")):
        if fld.get("type") == "slidenum":
            return True
    return False


def find_marker(slide, min_top_emu=None, names=LOCALE_NAMES):
    """The slide's page-number marker, in any of the three flavours.

    Flavour, not z-order, decides the winner. A single loop that returns on
    the first shape matching ANY branch lets whichever shape happens to sit
    first in the shape tree win regardless of which flavour it is - so a
    small numeric footnote near the marker floor, added before the real
    marker, would be returned instead of the real marker and then get
    overwritten with the page number while the real marker keeps its stale
    value. Instead every shape is classified once, in one walk, into the
    strongest flavour it matches (rank 0 strongest: real placeholder, then
    locale name, then field, then the literal heuristic), and the
    best-ranked candidate wins. Ties within a rank keep z-order, because the
    walk only replaces the current best on a STRICTLY better rank.
    """
    best_rank = None
    best_shape = None
    for shape in iter_shapes(slide.shapes):
        # The text-frame guard comes FIRST. A picture or group named
        # "Slide Number icon" would otherwise be classified by the name
        # branch, and set_number then dies on shape.text_frame.
        if not shape.has_text_frame:
            continue
        if shape.is_placeholder and shape.placeholder_format.type is not None \
                and "SLIDE_NUMBER" in str(shape.placeholder_format.type):
            rank = 0
        elif any(n in shape.name for n in names):
            rank = 1
        elif _has_slidenum_field(shape):
            rank = 2
        else:
            text = shape.text_frame.text.strip()
            if text.isdigit() and len(text) <= 3 and shape.top is not None \
                    and (min_top_emu is None or shape.top > min_top_emu):
                rank = 3
            else:
                continue
        if best_rank is None or rank < best_rank:
            best_rank = rank
            best_shape = shape
    return best_shape


def set_number(shape, text):
    """Force the marker to a literal number.

    A field renumbers itself to the file position, which is the wrong number
    the moment a slide is hidden or the cover is unnumbered - so the field is
    collapsed. Its run properties live inside it and are carried over, or the
    number lands in the theme's default face and size.
    """
    body = shape.text_frame._txBody
    paragraphs = body.findall(q("p"))
    para = paragraphs[0]
    keep = para.find(q("pPr"))

    rpr = None
    fld = para.find(q("fld"))
    if fld is not None and fld.find(q("rPr")) is not None:
        rpr = copy.deepcopy(fld.find(q("rPr")))
        rpr.attrib.pop("smtClean", None)
    if rpr is None:
        run = para.find(q("r"))
        if run is not None and run.find(q("rPr")) is not None:
            rpr = copy.deepcopy(run.find(q("rPr")))

    for child in list(para):
        if child is not keep:
            para.remove(child)
    run = etree.SubElement(para, q("r"))
    if rpr is not None:
        run.append(rpr)
    etree.SubElement(run, q("t")).text = text
    for extra in paragraphs[1:]:
        body.remove(extra)


def add_marker(slide, text, style):
    """A literal marker where none existed. Machine-built slides have none."""
    kwargs = {}
    if style.align is not None:
        kwargs["align"] = style.align
    return textbox(slide, style.x, style.y, style.w, style.h, text,
                   style.size, style.color, style.font, **kwargs)


def is_hidden(slide):
    """The hidden flag lives as show="0" on <p:sld> (catalogue item 7). OOXML's
    type is xsd:boolean, so "false" is accepted too - a deck hidden by a tool
    other than PowerPoint must not become visible to every reader at once."""
    return slide._element.get("show") in ("0", "false")


def visible_numbers(prs, skip=(1,)):
    """{file_position: printed_number or None} for every slide, mutating nothing.

    Hidden slides (`is_hidden`: `show="0"` on `<p:sld>`) consume no number and
    map to None; so do the VISIBLE positions named by `skip`. This is the
    single counting rule; `renumber` writes what it says and `notes.numbering`
    prints what it says, so the teleprompter and the footer cannot disagree.
    """
    out = {}
    visible = 0
    for position, slide in enumerate(prs.slides, 1):
        if is_hidden(slide):
            out[position] = None
            continue
        visible += 1
        out[position] = None if visible in skip else visible
    return out


def renumber(prs, style, skip=(1,)):
    """Rewrite every visible slide's printed number.

    Hidden slides are skipped and do not consume a number: the audience never
    sees them, so counting them puts every later number one too high. `skip`
    names VISIBLE positions that carry no number at all, the cover being the
    usual one - not file position, which a hidden slide before the cover
    would make ambiguous (visible index 1 and file position 1 would name two
    different slides, and no caller could say which was meant).

    The marker floor (`min_top_emu`, passed on to `find_marker`) is derived
    from `style.y` rather than taken as a parameter: the caller already
    supplies the marker's true position through `style`, and a second,
    independently-suppliable floor could silently disagree with it.
    """
    floor = px(style.y) - 1
    numbers = visible_numbers(prs, skip)
    report = []
    for position, slide in enumerate(prs.slides, 1):
        visible = numbers[position]
        if visible is None:
            continue
        marker = find_marker(slide, min_top_emu=floor)
        if marker is None:
            add_marker(slide, str(visible), style)
            report.append((position, visible, "added"))
        else:
            set_number(marker, str(visible))
            report.append((position, visible, "fixed"))
    return report
