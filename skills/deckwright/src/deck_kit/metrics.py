"""Measured text.

PowerPoint's autofit is never used - MSO_AUTO_SIZE must not appear
anywhere in this repository. All fitting happens here, offline, against
real TrueType files, and the builder places what it has measured.

The factors are empirical and face-specific, so they belong to the brand:
this module takes them as parameters and has no defaults of its own.
"""

import os
import sys

from PIL import ImageFont

PT_TO_PX = 96.0 / 72.0


def norm_runs(runs):
    """A bare string becomes one regular run; a run list is passed through.

    The one normalisation both halves of "measure with the same thing you
    write with" have to share. `primitives.settext` has always accepted a
    bare string - `textbox(..., "some copy", ...)` is what every builder and
    `brands/relay/style.py` itself write - and `TextMetrics.lines` did not:
    it iterated the string, read `"s"[1]` as a run's bold flag and raised
    `IndexError: string index out of range` from four frames inside the
    library, naming nothing about the caller. The two calls sit on adjacent
    lines in every builder, so they take the same argument.
    `primitives._norm` is this function; there is one definition, here,
    because metrics may not import primitives (pptx) and primitives may
    import metrics (PIL). Pinned by
    tests/test_metrics.py::test_lines_accepts_the_bare_string_settext_accepts.
    """
    if isinstance(runs, str):
        return [(runs, False)]
    return runs


class TextMetrics:
    """Measure text as PowerPoint will lay it out.

    font_dir      directory holding the two faces
    regular, bold face filenames within it
    width_factor  padding applied to every measurement, because PowerPoint
                  renders looser than PIL measures
    wrap_factor   the smaller padding used when simulating line wrapping
    pt_to_px      points to CSS pixels; the face is loaded at canvas scale.
                  The one value that is a unit conversion rather than a
                  calibration, so it is the only one with a default.

    Everything else is required. The factors were calibrated against one type
    family, so a brand that forgets to supply them must fail loudly rather
    than silently inherit another brand's calibration.
    """

    def __init__(self, font_dir, regular, bold, width_factor, wrap_factor,
                 pt_to_px=PT_TO_PX):
        self.font_dir = str(font_dir)
        self.files = {False: regular, True: bold}
        self.pt_to_px = pt_to_px
        self.width_factor = width_factor
        self.wrap_factor = wrap_factor
        self._cache = {}

    def _font(self, bold, pt):
        size = int(round(pt * self.pt_to_px))
        key = (bold, size)
        if key not in self._cache:
            path = os.path.join(self.font_dir, self.files[bold])
            self._cache[key] = ImageFont.truetype(path, size)
        return self._cache[key]

    def width(self, text, pt, bold=False, factor=None, spc=0):
        """Rendered width in CSS pixels, padded.

        `spc` is letter-spacing in points - the same unit `settext` takes -
        and it is added AFTER the padding factor rather than multiplied by
        it. The factor is a calibration of how much looser PowerPoint sets
        glyphs than PIL measures them; tracking is an exact number of points
        the renderer inserts after every character, this measurement's
        included, so scaling it by a fudge factor would make a -0.04em
        display line measure narrower than it is drawn.

        Measuring without it is not a rounding error: at Relay's +0.12em on
        a 10 pt mono label, tracking is a fifth of the line's width.
        """
        f = self.width_factor if factor is None else factor
        base = self._font(bold, pt).getlength(text) * f
        return base + (len(text) * spc * self.pt_to_px if spc else 0.0)

    def lines(self, runs, pt, avail, spc=0):
        """Greedy wrap simulation over mixed bold and regular runs.

        Measuring the concatenated string as a single weight under-counts
        when part of it is bold, so every word carries its own weight.
        """
        words = []
        # A run is (text, bold) or (text, bold, colour): the same shape
        # settext and add_para accept, so a builder can measure exactly the
        # runs it is about to write. Unpacking two fields rejected the
        # three-field form with a ValueError. A bare string is normalised
        # here for the same reason settext normalises one - see norm_runs.
        for run in norm_runs(runs):
            text, bold = run[0], run[1]
            words += [(w, bold) for w in text.split()]
        if not words:
            return 1
        space = self.width(" ", pt, False, self.wrap_factor, spc)
        count, cur = 1, 0.0
        for word, bold in words:
            ww = self.width(word, pt, bold, self.wrap_factor, spc)
            if cur == 0:
                cur = ww
            elif cur + space + ww <= avail:
                cur += space + ww
            else:
                count += 1
                cur = ww
        return count

    def fits(self, text, pt, bold, avail, spc=0):
        return self.width(text, pt, bold, spc=spc) <= avail


class WarnRegister:
    """Build-time overflow register.

    A clean build prints nothing and exits zero. A dirty one exits
    non-zero: in deckwright the zero-warning rule is enforced, not merely
    reported.
    """

    def __init__(self):
        self._entries = set()

    def add(self, tag, message):
        self._entries.add("%s %s" % (tag, message))

    @property
    def clean(self):
        return not self._entries

    def dump(self):
        return "\n".join(sorted(self._entries))

    def exit_if_dirty(self, stream=None):
        stream = sys.stdout if stream is None else stream
        if self.clean:
            print("no warnings", file=stream)
            return
        print(self.dump(), file=stream)
        raise SystemExit("build has %d overflow warning(s)" % len(self._entries))


def block_h(parts, gap=0):
    """Total height of a stack of measured parts, plus the gaps between them.

    Measure-then-place: compute this first, then derive the top from the
    container so the block sits centred, rather than asking PowerPoint to
    make it fit.
    """
    parts = list(parts)
    if not parts:
        return 0.0
    return float(sum(parts) + gap * (len(parts) - 1))
