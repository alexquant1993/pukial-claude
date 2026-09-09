import pytest
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.oxml.ns import qn

from deck_kit.xmlfill import alpha_fill, dashed, grad

BLUE = RGBColor(0x25, 0x63, 0xEB)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)


@pytest.fixture
def shape():
    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    return slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, 100, 100)


def test_alpha_fill_writes_a_solid_fill_with_an_alpha_child(shape):
    alpha_fill(shape, WHITE, 42)
    solid = shape._element.spPr.find(qn("a:solidFill"))
    alpha = solid.find(qn("a:srgbClr")).find(qn("a:alpha"))
    assert alpha is not None
    assert alpha.get("val") == "42000"


def test_grad_writes_native_gradient_xml_not_a_picture(shape):
    grad(shape, [(0, BLUE, 10), (100, BLUE, 55)], ang=0)
    g = shape._element.spPr.find(qn("a:gradFill"))
    assert g is not None
    stops = g.find(qn("a:gsLst")).findall(qn("a:gs"))
    assert [s.get("pos") for s in stops] == ["0", "100000"]
    assert g.find(qn("a:lin")).get("ang") == "0"


def test_grad_converts_degrees_to_sixtieths_of_a_degree(shape):
    grad(shape, [(0, BLUE, 100), (100, WHITE, 100)], ang=90)
    assert shape._element.spPr.find(qn("a:gradFill")).find(qn("a:lin")).get("ang") == "5400000"


def test_grad_replaces_any_existing_fill(shape):
    shape.fill.solid()
    grad(shape, [(0, BLUE, 100), (100, WHITE, 100)], ang=0)
    spPr = shape._element.spPr
    assert spPr.find(qn("a:solidFill")) is None
    assert spPr.find(qn("a:gradFill")) is not None


def test_grad_requires_an_explicit_angle(shape):
    """The engagement had two defaults, 0 and 90, so merging helpers by
    name silently rotated gradients. There is no default here."""
    with pytest.raises(TypeError):
        grad(shape, [(0, BLUE, 100), (100, WHITE, 100)])


def test_grad_rejects_two_tuple_stops_with_a_clear_message(shape):
    with pytest.raises(ValueError, match="position, colour, alpha"):
        grad(shape, [(0, BLUE), (100, WHITE)], ang=0)


def test_dashed_sets_colour_width_and_dash_style(shape):
    dashed(shape, BLUE, lw=0.9)
    assert shape.line.color.rgb == BLUE
    assert shape.line.width.pt == pytest.approx(0.9)
    assert shape.line.dash_style is not None


def test_grad_normalises_a_negative_angle(shape):
    """a:lin/@ang is a positive fixed angle. A negative value is
    schema-invalid, which is exactly the package PowerPoint offers to
    repair - and this repository's whole QA loop is "opens twice, no
    repair"."""
    grad(shape, [(0, BLUE, 100), (100, WHITE, 100)], ang=-90)
    ang = int(shape._element.spPr.find(qn("a:gradFill")).find(qn("a:lin")).get("ang"))
    assert 0 <= ang < 21600000
    assert ang == 270 * 60000


def test_grad_normalises_an_over_range_angle(shape):
    grad(shape, [(0, BLUE, 100), (100, WHITE, 100)], ang=450)
    ang = int(shape._element.spPr.find(qn("a:gradFill")).find(qn("a:lin")).get("ang"))
    assert ang == 90 * 60000


def test_alpha_fill_is_idempotent(shape):
    """Two calls used to stack two <a:alpha> children, whose resolution
    PowerPoint does not define."""
    alpha_fill(shape, WHITE, 42)
    alpha_fill(shape, WHITE, 72)
    clr = shape._element.spPr.find(qn("a:solidFill")).find(qn("a:srgbClr"))
    alphas = clr.findall(qn("a:alpha"))
    assert len(alphas) == 1
    assert alphas[0].get("val") == "72000"
