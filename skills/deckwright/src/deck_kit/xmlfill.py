"""Fills python-pptx cannot express, written as OOXML on the shape.

Linear gradients stay native so the deck remains editable: only conic
fills, which DrawingML has no element for, are pre-rendered to PNG.
"""

from pptx.enum.dml import MSO_LINE_DASH_STYLE
from pptx.oxml import parse_xml
from pptx.oxml.ns import nsdecls, qn
from pptx.util import Pt


def alpha_fill(shape, rgb, pct):
    """Solid fill at `pct` percent opacity.

    Idempotent: calling it twice replaces the alpha rather than stacking two
    conflicting <a:alpha> children, whose resolution PowerPoint does not
    define.
    """
    shape.fill.solid()
    shape.fill.fore_color.rgb = rgb
    clr = shape._element.spPr.find(qn("a:solidFill")).find(qn("a:srgbClr"))
    for existing in clr.findall(qn("a:alpha")):
        clr.remove(existing)
    clr.append(parse_xml('<a:alpha %s val="%d"/>' % (nsdecls("a"), int(pct * 1000))))


def grad(shape, stops, ang):
    """Linear gradient.

    stops: [(position 0-100, RGBColor, alpha percent), ...]
    ang:   degrees, required. No default - the engagement carried two
           conflicting ones and merging them rotated gradients silently.
           Normalised into 0..360, because a:lin/@ang is a positive fixed
           angle and a negative or over-range value is schema-invalid - which
           is exactly the kind of package PowerPoint offers to repair.
    """
    for stop in stops:
        if len(stop) != 3:
            raise ValueError(
                "each stop is (position, colour, alpha); got %d values" % len(stop))
    spPr = shape._element.spPr
    for tag in ("a:noFill", "a:solidFill", "a:gradFill"):
        for e in spPr.findall(qn(tag)):
            spPr.remove(e)
    gs = "".join(
        '<a:gs pos="%d"><a:srgbClr val="%02X%02X%02X"><a:alpha val="%d"/></a:srgbClr></a:gs>'
        % (int(p * 1000), c[0], c[1], c[2], int(a * 1000)) for p, c, a in stops)
    g = parse_xml(
        '<a:gradFill %s><a:gsLst>%s</a:gsLst><a:lin ang="%d" scaled="1"/></a:gradFill>'
        % (nsdecls("a"), gs, int((ang % 360) * 60000)))
    ln = spPr.find(qn("a:ln"))
    if ln is not None:
        ln.addprevious(g)
    else:
        spPr.append(g)


def dashed(shape, color, lw=1.0):
    shape.line.color.rgb = color
    shape.line.width = Pt(lw)
    shape.line.dash_style = MSO_LINE_DASH_STYLE.DASH
