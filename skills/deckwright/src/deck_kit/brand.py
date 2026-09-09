"""The template contract, as data.

A brand declares what its template must provide. `make_template.py`
produces a deck satisfying this; `inspect_template.py` reports an
existing corporate deck against it, clause by clause. A contract that no
artifact expresses and no code checks is not a contract.
"""

import importlib.util
import os
from dataclasses import dataclass
from pathlib import Path

from .geometry import CANVAS_H, CANVAS_W, EMU

_REPO_BRANDS = Path(__file__).resolve().parents[2] / "brands"


def brands_dir():
    """Where brand packages live.

    Resolved per call, not at import: DECKWRIGHT_BRANDS is how a caller points
    the library at brands that are not siblings of the source tree, which is
    every case once deck_kit is installed as a wheel - the parents[2] fallback
    is a source-checkout convenience, not a contract.
    """
    env = os.environ.get("DECKWRIGHT_BRANDS")
    return Path(env) if env else _REPO_BRANDS


@dataclass
class BrandSpec:
    name: str
    master_name: str
    layout_name: str
    canvas_w: int = CANVAS_W
    canvas_h: int = CANVAS_H
    background: str = "inherited"       # "inherited" or "drawn"
    sans: str = None
    serif: str = None
    font_dir: Path = None
    font_regular: str = None
    font_bold: str = None
    width_factor: float = None
    wrap_factor: float = None
    # The other two type roles a design system usually names. Optional: a
    # brand with one family declares none of them and `metrics("display")`
    # hands back the sans metrics, which is what a one-family brand means by
    # "the display face". Each role carries its own factors because the
    # factors calibrate a face, not a repository - Space Grotesk and Public
    # Sans need different numbers, and sharing one would put the wrap
    # simulation of two families on whichever was measured last.
    display: str = None
    display_regular: str = None
    display_bold: str = None
    display_width_factor: float = None
    display_wrap_factor: float = None
    mono: str = None
    mono_regular: str = None
    mono_bold: str = None
    mono_width_factor: float = None
    mono_wrap_factor: float = None
    logo_primary: Path = None
    logo_secondary: Path = None
    icon_dir: Path = None
    expects_embedded_fonts: int = 0     # reported, never asserted

    def __post_init__(self):
        for field in ("master_name", "layout_name"):
            value = getattr(self, field)
            if not isinstance(value, str):
                raise TypeError(
                    "%s must be selected by name, not by index - an index is "
                    "true of exactly one file" % field)
            # An empty name is an index in disguise, and the disguise works:
            # `spec.master_name in [m.name for m in prs.slide_masters]` passes
            # against a corporate deck whose four masters are all called '',
            # and deck._layout then resolves to whichever unnamed master
            # python-pptx yields first - which is a binding by position,
            # true of exactly one file, wearing a name-shaped mask. A real
            # corporate template arriving with unnamed masters is the normal
            # case, so the remedy is named where it is hit:
            # scripts/inspect_template.py prints it under the failed clause.
            # tests/test_brand.py::test_brand_spec_rejects_an_empty_name.
            if not value.strip():
                raise ValueError(
                    "%s must be selected by name, not by index - an empty "
                    "name binds to whichever master or layout comes first. "
                    "Name the master in PowerPoint's Slide Master view, or "
                    "generate a template with make_template.py" % field)
        # Not a dataclass field: one TextMetrics per role, kept because
        # TextMetrics caches loaded faces by size and a fresh one per call
        # would reload the TTF for every measurement a builder takes.
        self._metrics = {}

    def _role_fields(self, role):
        """The five field names that describe one type role.

        A table rather than getattr("%s_regular" % role) so that "sans" - the
        role whose fields predate the other two and are unprefixed - is
        described the same way as the rest, and so a typo in a role name
        raises here rather than resolving to None and falling back silently.
        """
        table = {
            "sans": ("sans", "font_regular", "font_bold",
                     "width_factor", "wrap_factor"),
            "display": ("display", "display_regular", "display_bold",
                        "display_width_factor", "display_wrap_factor"),
            "mono": ("mono", "mono_regular", "mono_bold",
                     "mono_width_factor", "mono_wrap_factor"),
        }
        if role not in table:
            raise ValueError("no such type role: %r (have %s)"
                             % (role, ", ".join(sorted(table))))
        return table[role]

    def declares(self, role):
        """Whether this brand names a family of its own for `role`."""
        return getattr(self, self._role_fields(role)[0]) is not None

    def family(self, role="sans"):
        """The family name a builder writes into the PPTX for `role`.

        Falls back to the sans family when the brand names none: a brand with
        one type family sets its display lines in that family, and a style
        helper written for three roles must keep working against it
        unchanged. tests/test_brand.py::test_a_one_family_brand_answers_every_role.
        """
        if not self.declares(role):
            role = "sans"
        return getattr(self, self._role_fields(role)[0])

    def metrics(self, role="sans"):
        """Build the brand's TextMetrics for one type role.

        Every calibrated value comes from here, so no brand can silently
        inherit another brand's numbers - and, since the factors calibrate a
        face rather than a repository, no role can silently inherit another
        role's either. A brand that declares no family for `role` measures it
        against its sans, which is the same fallback `family()` makes.

        `metrics()` with no argument is what it always was.
        """
        from .metrics import TextMetrics
        if not self.declares(role):
            role = "sans"
        if role in self._metrics:
            return self._metrics[role]
        _, regular, bold, width, wrap = self._role_fields(role)
        missing = [f for f in ("font_dir", regular, bold, width, wrap)
                   if getattr(self, f) is None]
        if missing:
            raise ValueError(
                "brand %r does not supply %s for the %s role; measurement "
                "factors are face-specific and have no sensible default"
                % (self.name, ", ".join(missing), role))
        built = TextMetrics(self.font_dir, getattr(self, regular),
                            getattr(self, bold), getattr(self, width),
                            getattr(self, wrap))
        self._metrics[role] = built
        return built

    def faces(self):
        """[(role, family, regular_file, bold_file)] for every role declared.

        What a check that the files are on disk walks, and what
        `tests/test_brand.py` uses so a face added to a brand is covered
        without the test being edited.
        """
        out = []
        for role in ("sans", "display", "mono"):
            if not self.declares(role):
                continue
            _, regular, bold, _, _ = self._role_fields(role)
            out.append((role, self.family(role),
                        getattr(self, regular), getattr(self, bold)))
        return out

    @property
    def slide_size_emu(self):
        return (self.canvas_w * EMU, self.canvas_h * EMU)

    @property
    def style_path(self):
        """The brand's style module sits next to its brand module."""
        base = self.font_dir.parent if self.font_dir else brands_dir() / self.name
        return base / "style.py"

    def style(self):
        return _load_module("brand_style_%s" % self.name, self.style_path)


def _load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_brand(name, brands_dir=None):
    root = Path(brands_dir) if brands_dir is not None else globals()["brands_dir"]()
    path = root / name / "brand.py"
    if not path.exists():
        raise ValueError("no such brand: %s (looked in %s)" % (name, path))
    return _load_module("brands_%s_brand" % name, path).BRAND
