"""SKILL.md structure: five task routes, every link resolving to a heading that exists.

Reads markdown on purpose - the artifact under test is the markdown.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "SKILL.md"
ROUTES = ["Build a new slide", "Integrate a version into the author's deck",
          "Diagnose a deck that will not open", "Set up a brand", "Run QA"]
LINK = re.compile(r"\]\((references/\d\d-[a-z-]+\.md)(#[a-z0-9-]+)?\)")


def _slug(heading):
    text = heading.lstrip("#").strip().lower()
    text = re.sub(r"[`*_]", "", text)
    text = re.sub(r"[^a-z0-9 -]", "", text)
    return re.sub(r"\s+", "-", text.strip())


def _anchors(path):
    """Headings only. Lines inside a fenced block are skipped: references/05's
    annotated rules TOML is full of `#` comments, and without the toggle any of
    them could satisfy an anchor that no real heading answers."""
    out = set()
    fenced = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("```"):
            fenced = not fenced
            continue
        if not fenced and line.startswith("#"):
            out.add(_slug(line))
    return out


INTAKE = "Before any route: the intake"
REQUIREMENTS = "Requirements"


def test_skill_has_exactly_the_five_routes_in_order():
    """Requirements, then the intake, then the routes. Neither of the first
    two is a route: the requirements are the machine, checked once before
    anything is asked, and the intake is asked once before any deck,
    whichever route follows."""
    heads = [l[3:].strip() for l in SKILL.read_text(encoding="utf-8").splitlines()
             if l.startswith("## ")]
    assert heads[0] == REQUIREMENTS
    assert heads[1] == INTAKE
    assert heads[2:] == ROUTES


def test_the_requirements_block_names_the_browser_as_required():
    """Session 2026-09-10, "capture is a requirement": an agent that cannot
    screenshot its drafts cannot judge them. The block has to say that a
    browser is required and that PowerPoint is not, because the reader who
    needs it is deciding what to install before question 1."""
    text = SKILL.read_text(encoding="utf-8")
    body = text.split("## " + REQUIREMENTS)[1].split("\n## ")[0]
    assert "scripts/doctor.py" in body
    assert "cannot see its own drafts" in body
    assert "DECKWRIGHT_BROWSER" in body
    browser = [l for l in body.splitlines() if "capture_drafts.py` can drive" in l]
    assert len(browser) == 1 and "**required**" in browser[0], browser
    powerpoint = [l for l in body.splitlines() if "PowerPoint" in l and l.startswith("|")]
    assert len(powerpoint) == 1 and "| optional |" in powerpoint[0], powerpoint


def test_the_intake_runs_the_doctor_before_its_first_question():
    """Step 0, and it has to be before question 1: a missing requirement is
    cheaper to fix before a spec is agreed than after ten drafts are
    written."""
    text = SKILL.read_text(encoding="utf-8")
    body = text.split("## " + INTAKE)[1].split("\n## ")[0]
    assert "scripts/doctor.py" in body
    assert body.index("doctor.py") < body.index("1. **Design system.**")


def test_the_draft_step_refuses_to_proceed_without_a_capture():
    """The route's own instruction, not a reference's: an agent following
    "Build a new slide" must be told to look at every draft, and told what
    to do when it cannot."""
    text = SKILL.read_text(encoding="utf-8")
    body = text.split("## Build a new slide")[1].split("\n## ")[0]
    for needle in ("capture_drafts.py", "look at it", "stop", "ledger",
                   "doctor.py", "DECKWRIGHT_BROWSER"):
        assert needle in body, needle


def test_the_intake_section_names_its_tools_and_the_front_matter_lines():
    """Session 2026-09-08 rulings: each of the three questions names the tool
    it runs and the spec line it fills, so an agent reading only SKILL.md
    can ask them."""
    text = SKILL.read_text(encoding="utf-8")
    body = text.split("## " + INTAKE)[1].split("\n## ")[0]
    for needle in ("scripts/discover.py", "**Design system:**", "**HTML draft:**",
                   "**Notes:**", "--notes", "brands/relay", "skipped:"):
        assert needle in body, "the intake does not name %r" % needle


def test_every_skill_route_resolves_to_an_existing_heading():
    text = SKILL.read_text(encoding="utf-8")
    links = LINK.findall(text)
    # derived from SKILL.md, section by section: 5 intake links + 5 + 9 + 3 +
    # 5 + 7 route links, and none in the preamble.
    # "Set up a brand" gained one, to the Relay adoption account in
    # references/02-html-stage.md. The 2026-09-10 output ruling added two to
    # the intake (the HTML stage and the platform matrix), one to "Build a
    # new slide" (stop at the stage page) and one to "Run QA" (the HTML
    # deck's own loop). The 2026-09-10 skill audit added the fifth intake
    # link: question 2 now names the route vocabulary, because "route-B
    # slide" was a term the intake used before the reader could have met it.
    # The 2026-09-10 capture ruling added two more: the platform matrix from
    # the new Requirements block, and the capturing section from the draft
    # step that now has to look at what it drew.
    assert len(links) == 36, "SKILL.md link count changed; re-derive, do not relax"
    for rel, anchor in links:
        target = ROOT / rel
        assert target.exists(), rel
        if anchor:
            assert anchor[1:] in _anchors(target), "%s has no heading for %s" % (rel, anchor)


WINDOWS_ROUTES = {"Integrate a version into the author's deck",
                  "Diagnose a deck that will not open", "Run QA"}


def test_every_route_states_its_platform_requirement():
    """Spec section 9: SKILL.md states the Windows dependency at the router.
    The three routes that reach COM must say Windows; the two that do not
    must not claim it."""
    text = SKILL.read_text(encoding="utf-8")
    for route in ROUTES:
        body = text.split("## " + route)[1].split("\n## ")[0]
        needs = [l for l in body.splitlines() if l.startswith("**Needs:**")]
        assert len(needs) == 1, "route %r does not state what it needs exactly once" % route
        assert ("Windows" in needs[0]) == (route in WINDOWS_ROUTES), (route, needs[0])


def test_every_test_named_in_a_reference_exists():
    """A reference naming a test that does not exist is the same defect as a
    doctrine nobody checks (Phase 2, Task 10)."""
    defined = set()
    for path in (ROOT / "tests").glob("test_*.py"):
        defined |= set(re.findall(r"^def (test_[a-z_0-9]+)", path.read_text(encoding="utf-8"), re.M))
    named = set()
    for path in (ROOT / "references").glob("*.md"):
        named |= set(re.findall(r"test_[a-z_0-9]+", path.read_text(encoding="utf-8")))
    # `tests/test_merge.py::test_x` yields both the test name and the module
    # stem `test_merge`; stems are files, not tests, and must not be reported
    named -= {p.stem for p in (ROOT / "tests").glob("test_*.py")}
    missing = sorted(named - defined)
    assert missing == [], missing


def _front_matter():
    text = SKILL.read_text(encoding="utf-8")
    assert text.startswith("---\n"), "SKILL.md has no YAML front matter"
    block = text.split("---\n", 2)[1]
    return {k: v.strip() for k, v in
            (l.split(":", 1) for l in block.splitlines() if ":" in l and not l.startswith(" "))}


def test_the_description_passes_the_skill_frontmatter_rules():
    """skill-creator's own validator (scripts/quick_validate.py) refuses a
    description containing `<` or `>`, and caps it at 1024 characters. The
    description used to read `Idea -> binding spec -> HTML draft -> ...`, so
    the skill this repository IS could not be validated or packaged by the
    skill that creates skills. An arrow is not worth that."""
    fm = _front_matter()
    name, desc = fm["name"], fm["description"]
    assert re.match(r"^[a-z0-9-]+$", name), name
    assert len(name) <= 64
    assert "<" not in desc and ">" not in desc, "angle brackets in the description"
    assert len(desc) <= 1024, len(desc)


def test_the_description_names_what_a_user_would_actually_ask_for():
    """The description is the whole of the triggering mechanism: an agent sees
    the name and this line, and nothing else, when it decides whether to open
    the skill. A user asks for a deck, slides or a presentation far more often
    than for `python-pptx`, and since 2026-09-10 the deliverable may be an HTML
    deck with no PowerPoint anywhere - which the description has to say, or
    that whole output is invisible to the router."""
    desc = _front_matter()["description"].lower()
    for word in ("deck", "slides", "presentation", "pptx", "html",
                 "design system", "retext", "qa"):
        assert word in desc, "the description never says %r" % word


def test_the_intake_says_an_html_deliverable_needs_the_draft():
    """Questions 2 and 4 are not independent: the stage page is built out of
    the drafts, so `HTML draft: skipped` plus `Output: html` is a spec with
    nothing to build. Both questions have to say so, because the agent asks
    them one message apart and records the answers before either is acted on."""
    text = SKILL.read_text(encoding="utf-8")
    body = text.split("## " + INTAKE)[1].split("\n## ")[0]
    flat = lambda s: re.sub(r"\s+", " ", s.replace("**", ""))
    q2 = flat(body.split("2. **HTML draft.**")[1].split("3. **Speaker notes.**")[0])
    q4 = flat(body.split("4. **Output.**")[1])
    assert "question 4" in q2 and "only ship as `pptx`" in q2, q2
    assert "skipped the draft" in q4, q4


RUN_LINE = re.compile(r"^\s*Run:", re.M)
REPO_PATH = re.compile(r"(?:scripts|references|templates|examples|brands|src|tests|docs)"
                       r"/[A-Za-z0-9_./-]*[A-Za-z0-9_]")


def test_every_run_line_in_a_script_docstring_names_files_that_exist():
    """`Run:` is the line somebody pastes into a terminal, so a path in it that
    no longer exists is a broken instruction, not a stale comment. This caught
    `examples/ai-horizon/lint_html.toml` in scripts/lint_deck.py - a rules file
    the 2026-09-10 "one lint.toml per deck" ruling had merged away.

    Only the Run: block is checked, not the whole docstring: several docstrings
    deliberately name deleted things in prose (`brands/example2`,
    `examples/capability-matrix`) to say where their coverage went, and `out/`
    paths are build artifacts that a clean tree does not carry."""
    import ast
    bad = []
    for path in sorted((ROOT / "scripts").glob("*.py")):
        doc = ast.get_docstring(ast.parse(path.read_text(encoding="utf-8"))) or ""
        lines = doc.splitlines()
        starts = [i for i, l in enumerate(lines) if RUN_LINE.match(l)]
        for start in starts:
            block = []
            for line in lines[start:]:
                if block and not line.strip():
                    break
                block.append(line)
            for named in REPO_PATH.findall("\n".join(block)):
                if not (ROOT / named).exists():
                    bad.append("%s: %s" % (path.name, named))
    assert bad == [], bad


def test_every_reference_file_is_named_in_skill_md():
    """Named, not routed: `00-pipeline.md` is reached only through SKILL.md's
    preamble sentence, not from any of the five routes, so the old name
    over-claimed what this assertion checks."""
    text = SKILL.read_text(encoding="utf-8")
    for ref in sorted((ROOT / "references").glob("*.md")):
        assert "references/%s" % ref.name in text, "%s is orphaned from SKILL.md" % ref.name
