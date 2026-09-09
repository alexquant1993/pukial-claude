import pathlib
import re

import pytest

from deck_kit.metrics import TextMetrics, WarnRegister, block_h

# brands/relay's body role: Public Sans, with the factors calibrated for that
# face (brands/relay/brand.py's docstring carries the method and the OBSERVED
# numbers). Every golden value below was re-measured against these files when
# the repository dropped to one brand; none was converted from the old Noto
# figures by arithmetic.
FONT_DIR = "brands/relay/fonts"
REGULAR, BOLD = "PublicSans-Regular.ttf", "PublicSans-Bold.ttf"
WIDTH_FACTOR, WRAP_FACTOR = 1.11, 1.06


def build(width_factor=WIDTH_FACTOR, wrap_factor=WRAP_FACTOR):
    return TextMetrics(FONT_DIR, REGULAR, BOLD, width_factor, wrap_factor)


@pytest.fixture
def m():
    return build()


# --- golden values -------------------------------------------------------
# Absolute measurements against the committed Public Sans faces. Relative
# assertions cannot catch a drift in the calibration: a padding factor that
# moves from 1.11 to 1.15 keeps every ordering intact and still ships a deck
# whose text no longer fits. These numbers are the only thing that would
# notice, and they were measured once and pinned, never guessed.

def test_golden_width_regular(m):
    assert m.width("Feature Store", 9.5) == pytest.approx(92.13, abs=0.05)


def test_golden_width_bold(m):
    assert m.width("Feature Store", 9.5, bold=True) == pytest.approx(95.46, abs=0.05)


def test_golden_width_at_a_larger_size(m):
    assert m.width("Capability", 12.0) == pytest.approx(85.47, abs=0.05)


def test_golden_space_width(m):
    """The wrap simulator adds one of these between every pair of words."""
    assert m.width(" ", 9.5) == pytest.approx(3.33, abs=0.05)


def test_golden_wrap_line_count(m):
    text = "the analyst verdict retrains models and rules"
    assert m.lines([(text, False)], 8.5, avail=120) == 3
    assert m.lines([(text, False)], 8.5, avail=200) == 2
    assert m.lines([(text, False)], 8.5, avail=400) == 1


# --- the doctrine the factors serve --------------------------------------

def test_width_applies_the_padding_factor():
    """The raw PIL measurement is multiplied by the brand's width factor.

    The factor is headroom, not a correction: brands/relay/brand.py's
    calibration measured PowerPoint's advance over PIL's at within a percent
    of 1 at 24 pt for every face. What this asserts is that the factor is
    applied at all, and applied multiplicatively.
    """
    raw = build(width_factor=1.0)
    padded = build(width_factor=1.11)
    assert padded.width("Feature Store", 9.5) == pytest.approx(
        raw.width("Feature Store", 9.5) * 1.11)


def test_metrics_has_no_factor_defaults_of_its_own():
    """The factors were calibrated against one type family. A brand that
    forgets to supply them must fail loudly, not silently inherit another
    brand's calibration."""
    with pytest.raises(TypeError):
        TextMetrics(FONT_DIR)
    with pytest.raises(TypeError):
        TextMetrics(FONT_DIR, REGULAR, BOLD)


def test_brand_metrics_refuses_to_build_without_the_factors():
    from dataclasses import replace

    from deck_kit.brand import load_brand
    spec = load_brand("relay")
    assert spec.metrics() is not None
    with pytest.raises(ValueError, match="width_factor"):
        replace(spec, width_factor=None).metrics()


# --- widths and wrapping -------------------------------------------------

def test_width_is_monotonic_in_text_length_and_size(m):
    assert m.width("i", 10) < m.width("iii", 10)
    assert m.width("hello", 10) < m.width("hello", 14)


def test_bold_is_wider_than_regular_at_the_same_size(m):
    """"Feature Store", not "Capability": PIL loads a face at an integer
    PIXEL size, so at 9.5 pt (12 px) Public Sans Regular and Bold advance
    "Capability" to the same total and the strict inequality is not true of
    every string at every size. Measured, not assumed - "Feature Store" is
    wider bold at 9.5, 12 and 20 pt."""
    assert m.width("Feature Store", 9.5, bold=True) > m.width("Feature Store", 9.5)


def test_lines_counts_one_line_when_everything_fits(m):
    assert m.lines([("short text", False)], 9.5, avail=1000) == 1


def test_lines_wraps_greedily_when_it_does_not_fit(m):
    text = "Feature Store aligned with the decision engine"
    one = m.width(text, 9.5)
    assert m.lines([(text, False)], 9.5, avail=one + 10) == 1
    assert m.lines([(text, False)], 9.5, avail=one / 2) >= 2


def test_lines_strictly_exceeds_the_regular_count_when_runs_are_bold(m):
    """Measuring a mixed-weight string as one weight under-counts. This is a
    strict inequality on purpose: with >= the test passes even if the
    per-word weight handling is deleted."""
    runs = [("Learning loop: ", True),
            ("the analyst verdict retrains models and rules", False)]
    flat = [("".join(t for t, _ in runs), False)]
    # 323 px, re-measured for Public Sans: its bold is much closer to its
    # regular than Noto Sans's was, so the old 336 has the two counts equal
    # and the strict inequality would have failed for the right reason.
    # 321..325 is the band where the mixed run wraps to 7 lines and the flat
    # one to 6.
    assert m.lines(runs, 8.5, 323) > m.lines(flat, 8.5, 323)


def test_lines_counts_bold_text_as_more_lines_than_the_same_text_regular(m):
    text = "Learning loop the analyst verdict retrains models and rules"
    # 86 px, re-measured: the 83..89 band is where bold takes one more line
    # than regular in Public Sans.
    assert m.lines([(text, True)], 8.5, 86) > m.lines([(text, False)], 8.5, 86)


def test_lines_never_returns_zero(m):
    assert m.lines([("", False)], 9.5, avail=100) == 1


def test_lines_survives_a_word_wider_than_the_whole_cell(m):
    assert m.lines([("Supercalifragilistic", False)], 9.5, avail=5) == 1
    assert m.lines([("two words", False)], 9.5, avail=5) == 2


def test_lines_ignores_empty_runs_among_real_ones(m):
    real = [("alpha beta gamma", False)]
    padded = [("", True), ("alpha beta gamma", False), ("", False)]
    assert m.lines(padded, 9.5, 60) == m.lines(real, 9.5, 60)


def test_fits_is_width_against_available(m):
    w = m.width("Capability", 9.5, bold=True)
    assert m.fits("Capability", 9.5, True, w + 1)
    assert not m.fits("Capability", 9.5, True, w - 1)


# --- block height --------------------------------------------------------

def test_block_h_sums_parts_and_gaps():
    assert block_h([10, 20, 30], gap=4) == 68.0


def test_block_h_of_a_single_part_has_no_gap():
    assert block_h([10], gap=4) == 10.0


def test_block_h_of_nothing_is_zero():
    assert block_h([], gap=4) == 0.0


def test_block_h_is_what_measure_then_place_centres_on():
    """The idiom: measure the block, then derive the top from the container.
    Nothing asks PowerPoint to make it fit."""
    parts, gap, container_h = [23, 32, 23], 3, 120
    total = block_h(parts, gap)
    top = (container_h - total) / 2.0
    assert top + total <= container_h
    assert top == pytest.approx((120 - 84) / 2.0)


# --- the warning register ------------------------------------------------

def test_warn_register_starts_clean_and_records_tagged_entries():
    w = WarnRegister()
    assert w.clean
    w.add("OVERFLOW", "cell 3 is 12 px over")
    assert not w.clean
    assert "OVERFLOW" in w.dump()
    assert "cell 3 is 12 px over" in w.dump()


def test_warn_register_deduplicates_and_sorts():
    """The same overflow fires once per cell; an undeduplicated dump is
    unreadable."""
    w = WarnRegister()
    w.add("WRAP", "b")
    w.add("WRAP", "a")
    w.add("WRAP", "b")
    assert w.dump().splitlines() == ["WRAP a", "WRAP b"]


def test_warn_register_exits_non_zero_when_dirty():
    w = WarnRegister()
    w.add("HEIGHT", "too tall")
    with pytest.raises(SystemExit) as e:
        w.exit_if_dirty()
    assert e.value.code != 0


def test_warn_register_does_not_exit_when_clean(capsys):
    WarnRegister().exit_if_dirty()
    assert "no warnings" in capsys.readouterr().out


IMPORTS_AUTOFIT = re.compile(r"^\s*(from .*import .*MSO_AUTO_SIZE|import .*MSO_AUTO_SIZE)", re.M)


def test_repository_never_imports_autofit():
    """Necessary but nowhere near sufficient: autofit reaches a deck from a
    python-pptx default, not from an import, so the real check is
    scripts/assert_native.py against the built package.
    """
    offenders = []
    for path in pathlib.Path(".").rglob("*.py"):
        if {".venv", "out", ".pytest_cache"} & set(path.parts):
            continue
        if IMPORTS_AUTOFIT.search(path.read_text(encoding="utf-8")):
            offenders.append(str(path))
    assert offenders == []


def test_lines_accepts_the_three_field_runs_settext_writes(m):
    """A run is (text, bold) or (text, bold, colour), the shape settext and
    add_para accept. A builder measures the runs it is about to write, and
    the coloured form used to raise ValueError inside the wrap simulator."""
    two = [("Learning loop: ", True), ("the analyst verdict retrains", False)]
    three = [("Learning loop: ", True, (1, 2, 3)), ("the analyst verdict retrains", False, None)]
    assert m.lines(three, 9.5, 120) == m.lines(two, 9.5, 120)


def test_lines_accepts_the_bare_string_settext_accepts(m):
    """`textbox(..., "some copy", ...)` is idiomatic, and the doctrine of the
    PPTX stage is "measure with the same thing you write with", so the two
    calls sit on adjacent lines in every builder. `lines` used to iterate the
    string and raise IndexError from inside the library, naming nothing about
    the caller."""
    copy = "the analyst verdict retrains the model overnight"
    assert m.lines(copy, 9.5, 120) == m.lines([(copy, False)], 9.5, 120)
    assert m.lines(copy, 9.5, 120) > 1
    assert m.lines("", 9.5, 120) == 1


def test_primitives_and_metrics_share_one_run_normalisation():
    """One definition, so a bare string cannot mean one thing to the writer
    and another to the measurer."""
    from deck_kit import primitives
    from deck_kit.metrics import norm_runs
    assert primitives._norm is norm_runs


# --- letter-spacing ------------------------------------------------------
# Relay's display type is set at -0.035em and its mono labels at +0.12em, so
# a measurement that ignores tracking is wrong by a fifth of a label's width.

def test_tracking_widens_a_measurement_by_an_exact_number_of_points(m):
    """Not an estimate: PowerPoint inserts `spc` after every character, this
    string's last one included, so the delta is len(text) x spc, converted
    from points to CSS pixels."""
    from deck_kit.metrics import PT_TO_PX
    plain = m.width("HOW TO READ THIS", 9.9)
    tracked = m.width("HOW TO READ THIS", 9.9, spc=9.9 * 0.12)
    assert tracked - plain == pytest.approx(len("HOW TO READ THIS") * 9.9 * 0.12 * PT_TO_PX,
                                            abs=0.01)


def test_negative_tracking_narrows_a_measurement(m):
    assert m.width("Relay", 30.0, bold=True, spc=-30.0 * 0.035) < m.width("Relay", 30.0, bold=True)


def test_tracking_is_added_after_the_padding_factor_not_multiplied_by_it():
    """The factor calibrates glyph advances; tracking is exact. Scaling it
    would make a tightly-tracked display line measure narrower than drawn."""
    raw, padded = build(width_factor=1.0), build(width_factor=1.12)
    delta_raw = raw.width("LABEL", 10.0, spc=1.2) - raw.width("LABEL", 10.0)
    delta_padded = padded.width("LABEL", 10.0, spc=1.2) - padded.width("LABEL", 10.0)
    assert delta_raw == pytest.approx(delta_padded, abs=0.001)


def test_tracking_reaches_the_wrap_simulator(m):
    """A label that fits untracked and does not fit tracked must wrap; a
    wrap count blind to tracking is the overflow nobody sees."""
    runs = [("Signposts that move the dates", True)]
    avail = m.width("Signposts that move the dates", 12.0, bold=True) + 4
    assert m.lines(runs, 12.0, avail) == 1
    assert m.lines(runs, 12.0, avail, spc=12.0 * 0.12) > 1


def test_fits_takes_tracking_too(m):
    avail = m.width("BEYOND", 9.0, True) + 2
    assert m.fits("BEYOND", 9.0, True, avail)
    assert not m.fits("BEYOND", 9.0, True, avail, spc=9.0 * 0.12)
