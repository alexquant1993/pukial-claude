"""Structure checks on the templates and their filled instances.

These tests read markdown on purpose: the artifact under test IS the
markdown. They establish no doctrine about any .py file and are not listed
in test_no_source_grep_doctrines.py's package-opening lists.
"""

import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import lint_deck  # noqa: E402

TEMPLATES = ROOT / "templates"
WALK = ROOT / "examples" / "walkthrough"
PLACEHOLDER = re.compile(r"<[^<>\n]{1,120}>")   # any <angle placeholder>; the templates hold no legitimate angle-bracket text


def _h2(path):
    return [l.strip() for l in path.read_text(encoding="utf-8").splitlines()
            if l.startswith("## ")]


@pytest.mark.parametrize("name", ["spec.md", "handoff.md"])
def test_the_filled_instance_keeps_every_section_of_its_template(name):
    assert _h2(WALK / name) == _h2(TEMPLATES / name)


@pytest.mark.parametrize("name", ["spec.md", "handoff.md"])
def test_the_template_carries_placeholders_and_the_instance_carries_none(name):
    assert PLACEHOLDER.search((TEMPLATES / name).read_text(encoding="utf-8")), \
        "a template with nothing to fill in is a document, not a template"
    left = PLACEHOLDER.findall((WALK / name).read_text(encoding="utf-8"))
    assert left == [], "unfilled placeholders in the walkthrough: %s" % left


def test_the_handoff_template_ships_section_zero_filled_in():
    text = (TEMPLATES / "handoff.md").read_text(encoding="utf-8")
    zero = text.split("## 0.")[1].split("## 1.")[0]
    for phrase in ("never overwrite", "reading order", "defaults", "work directory"):
        assert phrase in zero.lower(), "section 0 does not state the %r rule" % phrase
    assert not PLACEHOLDER.search(zero), "section 0 is meant to ship filled, not blank"


def test_the_spec_template_and_the_walkthrough_spec_both_carry_an_exact_string_table():
    assert lint_deck.exact_strings_from_spec(TEMPLATES / "spec.md")
    assert lint_deck.exact_strings_from_spec(WALK / "spec.md") == [
        "Four stages and one loop.",
        "Three kinds of check: file, visual, content.",
    ]


INTAKE_LINES = ("**Design system:**", "**HTML draft:**", "**Notes:**",
                "**Output:**")
# The brand a deck is built on when the user brings none. scripts/discover.py
# holds the same name, and tests/test_discover.py asserts it recommends it.
DEFAULT_BRAND = "relay"
NOTES_MODES = {"none", "pptx", "teleprompter", "both"}
# The fourth intake answer. `html` is a first-class deliverable: the drafts
# become the deck, built into a stage page by scripts/build_html_deck.py,
# linted as a drafts directory and printed to PDF from the browser. `both`
# is the default because a deck usually has to arrive as a file somebody can
# edit as well.
OUTPUT_MODES = {"html", "pptx", "both"}


def _front_matter(path):
    """The lines before the first `---` rule, as {label: value}."""
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip() == "---":
            break
        for label in INTAKE_LINES + ("**Status:**",):
            if line.startswith(label):
                out[label] = line[len(label):].strip()
    return out


FILLED_SPECS = [WALK / "spec.md", ROOT / "examples" / "ai-horizon" / "spec.md"]


def test_the_spec_template_and_every_filled_spec_carries_the_intake_lines():
    """Session 2026-09-08 and 2026-09-10 rulings: the four intake answers
    live in the spec's front matter, after Status, in a fixed order and
    vocabulary."""
    template = (TEMPLATES / "spec.md").read_text(encoding="utf-8").split("\n---")[0]
    labels = [l.split(":**")[0] + ":**" for l in template.splitlines()
              if l.startswith("**")]
    assert labels[-5:] == ["**Status:**"] + list(INTAKE_LINES), labels
    fm = _front_matter(TEMPLATES / "spec.md")
    for label in INTAKE_LINES:
        assert PLACEHOLDER.fullmatch(fm[label]), (label, fm[label])
    for spec in FILLED_SPECS:
        fm = _front_matter(spec)
        assert set(INTAKE_LINES) <= set(fm), (spec, fm)
        assert fm["**Design system:**"], spec
        assert re.match(r"^(yes\b|skipped: \S)", fm["**HTML draft:**"]), (spec, fm)
        assert fm["**Notes:**"] in NOTES_MODES, (spec, fm)
        assert fm["**Output:**"] in OUTPUT_MODES, (spec, fm)


def test_the_output_line_offers_html_pptx_and_both():
    """The PPTX is optional: some users want the HTML deck and nothing else,
    and a pipeline that only asks about the file it always built cannot hear
    them. The template's placeholder names all three, and `both` is the
    default the intake proposes."""
    fm = _front_matter(TEMPLATES / "spec.md")["**Output:**"]
    assert set(re.findall(r"[a-z]+", fm)) == OUTPUT_MODES, fm
    skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    body = skill.split("## Before any route: the intake")[1].split("\n## ")[0]
    assert "**Output:**" in body
    assert "`html`" in body and "`both`" in body
    for reference in ("00-pipeline.md", "01-spec-stage.md", "02-html-stage.md",
                      "05-qa.md"):
        text = (ROOT / "references" / reference).read_text(encoding="utf-8")
        assert "**Output:**" in text or "`Output:`" in text or "Output:" in text, reference


def test_the_design_system_line_offers_no_pptx_master_route():
    """Ruling, session 2026-09-10: the pipeline always starts from a design
    system plus HTML examples. There is no route that adopts a corporate
    PPTX master as the identity, so the front matter must not offer one -
    the answer it invited could not be acted on."""
    fm = _front_matter(TEMPLATES / "spec.md")["**Design system:**"]
    assert "master" not in fm.lower(), fm
    assert "design system" in fm.lower() and "brands/relay" in fm


def test_every_filled_spec_names_a_design_system_that_exists():
    """The intake's first answer is a brand package or the default, and a
    spec naming a brand nobody built is a build that fails at load."""
    from deck_kit.brand import brands_dir
    for spec in FILLED_SPECS:
        answer = _front_matter(spec)["**Design system:**"]
        if answer.startswith("default"):
            assert "brands/%s" % DEFAULT_BRAND in answer, (spec, answer)
            continue
        name = answer.split()[0]
        assert (brands_dir() / name / "brand.py").is_file(), (spec, answer)


def test_the_spec_template_offers_the_default_design_system_by_name():
    """One name for "the default", in the template and in the reference that
    quotes it. Move the default and leave these behind and the intake writes
    a front-matter line naming a brand nobody builds on."""
    fm = _front_matter(TEMPLATES / "spec.md")["**Design system:**"]
    assert "default (brands/%s)" % DEFAULT_BRAND in fm, fm
    reference = (ROOT / "references" / "01-spec-stage.md").read_text(encoding="utf-8")
    assert "default (brands/%s)" % DEFAULT_BRAND in reference


def _routes(path):
    lines = path.read_text(encoding="utf-8").splitlines()
    for i, line in enumerate(lines):
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if "Route" in cells:
            col = cells.index("Route")
            out = []
            for row in lines[i + 2:]:
                if not row.strip().startswith("|"):
                    break
                rc = [c.strip() for c in row.strip().strip("|").split("|")]
                out.append(rc[col])
            return out
    raise AssertionError("%s has no slide table with a Route column" % path)


def test_every_walkthrough_slide_names_a_technical_route_from_the_vocabulary():
    routes = _routes(WALK / "spec.md")
    assert len(routes) == 2
    assert all(re.match(r"^[ABC]\b", r) for r in routes), routes
    assert _routes(TEMPLATES / "spec.md"), "the template's slide table has no rows"


RULING = re.compile(r"^- Ruling: .+? - cost if wrong: .+$", re.S)


def test_the_walkthrough_ledger_uses_the_ruling_grammar():
    text = (WALK / "ledger.md").read_text(encoding="utf-8")
    entries = [e.strip() for e in re.split(r"\n(?=- Ruling:)", text) if e.strip().startswith("- Ruling:")]
    assert len(entries) == 2, "the walkthrough ledger carries exactly two rulings"
    for e in entries:
        assert RULING.match(" ".join(e.split())), "not in the ruling grammar: %s" % e[:80]


# --- the AI horizon deck: the second filled spec, ten slides --------------

HORIZON = ROOT / "examples" / "ai-horizon"


def test_the_ai_horizon_spec_keeps_every_section_of_the_template():
    assert _h2(HORIZON / "spec.md") == _h2(TEMPLATES / "spec.md")
    assert PLACEHOLDER.findall((HORIZON / "spec.md").read_text(encoding="utf-8")) == []


def test_every_ai_horizon_slide_names_a_route_and_carries_a_draft():
    """Every slide is route B and every slide has a draft. This deck was
    drafted first, slide by slide, then ported - the pipeline's own order,
    and the reason its ledger has sixteen rulings and not five."""
    routes = _routes(HORIZON / "spec.md")
    assert len(routes) == 10
    assert all(re.match(r"^B\b", r) for r in routes), routes
    drafts = sorted(p.name for p in (HORIZON / "drafts").glob("*.html"))
    assert len(drafts) == 10, drafts


def test_the_ai_horizon_spec_pins_thirteen_exact_strings():
    """Ten forecasts and reading rules, plus the readiness claim and the two
    states its legend reads - added when S09 folded the deleted
    examples/capability-matrix's kit coverage into this deck."""
    exact = lint_deck.exact_strings_from_spec(HORIZON / "spec.md")
    assert len(exact) == 13
    assert "The dates will be wrong. The direction is the forecast." in exact
    assert "RED absent today" in exact
    assert "AMBER partial today" in exact


def test_the_ai_horizon_ledger_uses_the_ruling_grammar():
    text = (HORIZON / "ledger.md").read_text(encoding="utf-8")
    entries = [e.strip() for e in re.split(r"\n(?=- Ruling:)", text)
               if e.strip().startswith("- Ruling:")]
    # 16 design decisions, plus the 2026-09-10 capture ruling: SKILL.md's
    # draft step says a capture taken through a route other than Python
    # Playwright is recorded on the deck's ledger, and this deck's HTML
    # captures were taken with a browser binary.
    assert len(entries) == 17, "one ruling per design decision this deck took"
    for e in entries:
        assert RULING.match(" ".join(e.split())), "not in the ruling grammar: %s" % e[:80]


def test_the_ai_horizon_lint_rules_name_the_relay_brand_and_its_own_boilerplate():
    """A rules file copied from another deck and left pointing at the other
    brand's assets and copyright line passes every check for the wrong
    reason: the manifest it verifies is not this brand's."""
    import tomllib
    with open(HORIZON / "lint.toml", "rb") as fh:
        rules = tomllib.load(fh)
    assert rules["assets"]["brand"] == "relay"
    assert rules["required"]["strings"] == ["(C) RELAY - CONFIDENTIAL"]
    assert rules["exact"]["spec"] == "spec.md"
    # The vendor list is a content constraint rather than the brand's, and
    # the kicker allowlist is the spec's; both must be non-empty or the
    # checks run with no rules and are SKIPPED rather than passed.
    assert rules["forbidden"]["tokens"]
    assert rules["kickers"]["allowed"]
