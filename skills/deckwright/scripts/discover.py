"""Find what a new deck can build on: design systems, brand packages, token sheets.

The intake helper the skill runs before a deck is started. **A deck is built
from a design system and HTML examples**; there is no route in this
repository that adopts somebody's PPTX master as the identity, so the
question this script answers is "which design system?" and it has three
answers: one the user points at with `--design-system`, one found on disk,
or the default `brands/relay`.

What it reports, in plain text or as JSON (--json), with the recommendation
printed FIRST as well as last - the actionable line must not be the 563rd:

  pointed   the design system named by --design-system, verified and
            reported before anything else
  brands    every package under the brands dir (a directory with brand.py):
            name, master and layout names, whether tokens.css, fonts/ and
            icons/ exist next to it, and which of the faces its fonts.toml
            declares are not on disk yet
  systems   every directory that holds a design system but no brand.py -
            a downloaded system, in whatever shape it arrived in, that
            nothing in this repository can build a deck against yet
  masters   every *.pptx/*.potx/*.thmx under --root, grouped by directory.
            Reported as inventory, never as a recommendation: a master is
            not a design system, and this pipeline does not adopt one
  tokens    every tokens.css under --root

`out/`, `build/`, `dist/`, `_archive`, `.git`, `.venv`, `.superpowers` and
`node_modules` are never searched: a built deck under out/ is an output, not
something to adopt, and a build directory is where ninety copies of one
corporate template live.

A design system does not have to arrive in deckwright's shape, and no real
one has. `brands/relay_design_system/` had no `brand.py`, no `tokens.css`
and no master - its tokens were a `tokens/` directory of eight CSS files.
The next one had `colors_and_type.css`, a `README.md` and a `SKILL.md`, and
an earlier version of this script reported neither of them: it recognised
exactly three shapes, none of them that one, and named instead a sample UI
kit two levels inside the same system. The parent went unreported and the
child was recommended - the exact failure this script exists to prevent,
because a user who trusts the intake then builds their deck in the default
brand's palette.

So the evidence test is wider, and it prefers the OUTERMOST match: once a
directory qualifies, nothing below it is reported as a separate system.

  tokens/*.css            a directory of token sheets rather than one file
  styles.css              beside a readme.md or a SKILL.md
  <name>.css              a top-level sheet whose name carries the token
                          vocabulary - colors_and_type.css, theme.css,
                          brand-variables.css - beside a readme or a SKILL.md
  <name>.css (:root ...)  a top-level sheet that declares custom properties
                          on :root, which is a token sheet whatever it is
                          called, and is evidence on its own
  _ds_manifest.json       a system that ships its own manifest

The recommendation, in order: the system the user pointed at; then a brand
package that is not this repository's own default; then a design system
found on disk; then the default brand. A design system of the user's own
outranks `brands/relay`, because "the repository ships one brand" is not a
fact about the user's identity. Candidate masters never enter the
recommendation at all.

Exit 0 on a report, 2 when --root or --design-system does not exist.

Run: uv run --offline --no-project --with python-pptx --with pillow \
       python scripts/discover.py [--root PATH] [--brands PATH] \
       [--design-system PATH] [--json]
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
# fetch_fonts.py is a sibling script, and reading its manifest is how this
# report knows which declared faces are missing. sys.path[0] is already this
# directory when discover.py is run as a script; the insert is for an import.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pptx import Presentation  # noqa: E402

from deck_kit.brand import brands_dir, load_brand  # noqa: E402
from fetch_fonts import missing_fonts  # noqa: E402

MASTER_SUFFIXES = (".pptx", ".potx", ".thmx")
# build/ and dist/ join the list because that is where a real tree keeps its
# ninety copies of one corporate template: 80 of the 90 candidate masters in
# the run that prompted this were under one deck's build directory.
SKIPPED_DIRS = ("out", "build", "dist", "_archive", ".git", ".venv",
                ".superpowers", "node_modules", "__pycache__")
# What the report says when the user has no design system of their own.
DEFAULT_BRAND = "relay"

# A directory holding more than this many candidate masters is collapsed to
# one line in the text report. Five is the point past which the section stops
# being a list a human picks from and becomes a wall to scroll past.
MASTER_GROUP_LIMIT = 5
# Layout names printed per master before "(+N more)". A corporate master with
# a hundred layouts says nothing more in its ninety-fourth name.
LAYOUT_LIMIT = 6

# The vocabulary a design system names its token sheet with. Matched as a
# substring of the filename, so colors_and_type.css, brand-variables.css and
# theme.css are all recognised.
TOKEN_WORDS = ("color", "colour", "token", "style", "theme", "variable",
               "palette", "typograph", "brand")
# `:root { --x: ... }`, allowing other selectors in the same rule and any
# amount of whitespace. A sheet that declares custom properties on :root is a
# token sheet whatever its filename is.
ROOT_VARS = re.compile(r":root[^{}]*\{[^}]*--[A-Za-z0-9_-]+\s*:", re.S)
CSS_READ_LIMIT = 400_000


def find_brands(brands):
    """One record per directory under `brands` that carries a brand.py.

    A brand.py that does not load is reported with its error rather than
    skipped: a half-written brand is exactly what the person starting a deck
    needs to hear about.
    """
    found = []
    if not brands.is_dir():
        return found
    for entry in sorted(p for p in brands.iterdir() if (p / "brand.py").is_file()):
        record = {"name": entry.name, "path": str(entry)}
        try:
            spec = load_brand(entry.name, brands)
            record.update(master_name=spec.master_name, layout_name=spec.layout_name)
        except Exception as exc:  # any load failure: a syntax error, a missing import
            record["error"] = "%s: %s" % (type(exc).__name__, exc)
        record.update(
            tokens_css=(entry / "tokens.css").is_file(),
            fonts=(entry / "fonts").is_dir(),
            icons=(entry / "icons").is_dir(),
            # [(family, weight, file)] the brand's fonts.toml declares and
            # the disk does not have. A face is measured against before a
            # slide is placed, so this is the intake's own reason to run
            # scripts/fetch_fonts.py rather than a nice-to-have.
            missing_fonts=[list(f) for f in missing_fonts(entry)],
        )
        found.append(record)
    return found


def _walk(root):
    """Files under root, pruned at the directories a search must not enter."""
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIPPED_DIRS)
        for name in sorted(filenames):
            yield Path(dirpath) / name


def read_masters(path):
    """[{name, layouts}] for every slide master python-pptx finds in `path`."""
    prs = Presentation(str(path))
    return [{"name": m.name, "layouts": [l.name for l in m.slide_layouts]}
            for m in prs.slide_masters]


def find_masters(root):
    """Candidate corporate masters: one record per deck-like file under root.

    Inventory, not a route. This repository builds from a design system and
    HTML examples; a .pptx somebody dropped in is reported so the user knows
    what is on the machine, and is never recommended.
    """
    found = []
    for path in _walk(root):
        if path.suffix.lower() not in MASTER_SUFFIXES:
            continue
        record = {"path": str(path.relative_to(root))}
        try:
            record["masters"] = read_masters(path)
        except Exception as exc:  # python-pptx raises several types; none may
            # become a traceback in an intake report
            record["error"] = "%s: %s" % (type(exc).__name__, exc)
        found.append(record)
    return found


def find_tokens(root):
    return [str(p.relative_to(root)) for p in _walk(root) if p.name == "tokens.css"]


def _names(d):
    """The directory entry names, lowercased, or an empty set.

    Lowercased because the two evidence files that carry a conventional
    case - `readme.md` and `SKILL.md` - are written both ways in the wild. A
    case-sensitive filesystem would otherwise miss a system whose readme is
    `README.md`, which is most of them.
    """
    try:
        return {q.name.lower() for q in d.iterdir()}
    except OSError:
        return set()


def _css_files(d):
    """Top-level .css filenames, sorted, or []."""
    try:
        return sorted(q.name for q in d.iterdir()
                      if q.is_file() and q.suffix.lower() == ".css")
    except OSError:
        return []


def _is_token_sheet(name):
    return any(word in name.lower() for word in TOKEN_WORDS)


def _declares_root_vars(path):
    """Whether `path` sets custom properties on :root.

    Read with a size cap and every read error swallowed: this runs over
    whatever the user's tree happens to hold, and an unreadable stylesheet is
    not evidence either way.
    """
    try:
        if path.stat().st_size > CSS_READ_LIMIT:
            return False
        return bool(ROOT_VARS.search(path.read_text(encoding="utf-8", errors="replace")))
    except OSError:
        return False


def system_holdings(d):
    """What design-system evidence directory `d` carries, in report order.

    Empty means this is not a design system. Any one of the shapes in the
    module docstring is enough on its own; the extras appended after them
    are reported so the user can see what they would be adopting - a system
    with an `assets/` directory has a logo, which the "Set up a brand" route
    needs to know - and never decide the question.
    """
    names = _names(d)
    holds = []
    tokens = d / "tokens"
    if tokens.is_dir() and any(q.suffix.lower() == ".css" and q.is_file()
                               for q in tokens.iterdir()):
        holds.append("tokens/*.css")

    css = _css_files(d)
    companion = bool({"readme.md", "skill.md"} & names)
    seen = set()
    # styles.css keeps its own line, because it is the shape the first
    # downloaded system arrived in and the reports name it that way.
    if "styles.css" in names and companion:
        holds.append("styles.css")
        seen.add("styles.css")
    # Any other top-level sheet whose NAME carries the token vocabulary,
    # beside a readme or a SKILL.md. This is the corporate-design-system case:
    # colors_and_type.css was a token sheet nothing recognised.
    if companion:
        for name in css:
            if name not in seen and _is_token_sheet(name):
                holds.append(name)
                seen.add(name)
    # And any top-level sheet that declares custom properties on :root,
    # whatever it is called and with no companion needed: a file that sets
    # `--brand-ink` on `:root` is a token sheet by construction.
    for name in css:
        if name not in seen and _declares_root_vars(d / name):
            holds.append("%s (:root tokens)" % name)
            seen.add(name)
    if "_ds_manifest.json" in names:
        holds.append("_ds_manifest.json")

    if not holds:
        return []
    for extra in ("guidelines", "ui_kits", "components", "fonts", "icons",
                  "slides", "preview", "assets"):
        if (d / extra).is_dir():
            holds.append(extra + "/")
    if (d / "assets" / "icons").is_dir():
        holds.append("assets/icons/")
    return holds


def _display(path, root):
    """`path` relative to root when it is under it, else absolute.

    The brands dir is a sibling of --root as often as it is a child, and
    relative_to raises on the sibling case rather than returning anything
    useful.
    """
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _under(child, parents):
    return any(child == p or p in child.parents for p in parents)


def system_strength(holds):
    """2 when the directory declares itself a design system, 1 when it only
    looks like one.

    A `tokens/` directory, a `_ds_manifest.json` or a named token sheet
    beside a readme is a system saying what it is. A stylesheet that happens
    to set custom properties on `:root` is weaker evidence and is often a
    deck's own working CSS - real: a deck directory holding `theme.css` and
    `dya-matrix.css` was reported alongside the actual design system, and
    sorted ahead of it by name alone. The report lists both; the
    recommendation names the stronger one.
    tests/test_discover.py::test_a_declared_system_is_recommended_over_a_directory_that_merely_has_root_vars.
    """
    primary = [h for h in holds
               if not h.endswith("/") and "(:root tokens)" not in h]
    return 2 if primary else 1


def find_systems(root, brands):
    """Design systems on disk that no brand package has been built from.

    Both trees are searched, and the brands dir explicitly, because a
    downloaded system usually lands next to the brand packages - which is
    where `brands/relay_design_system/` is - and the brands dir is not
    always under --root.

    **The outermost match wins.** Once a directory qualifies, nothing below
    it is walked: a design system ships sample UI kits, and each kit has a
    `styles.css` of its own. Reporting the kit and not the system is how the
    run that prompted this rewrite ended up naming
    `design_system/ui_kits/analytics-dashboard` while `design_system/` itself
    went unmentioned. A directory carrying a brand.py is a brand package
    rather than a loose system - find_brands reports it - and is pruned for
    the same reason: its internals are not separate systems either.
    tests/test_discover.py::test_the_outermost_directory_is_the_system_not_the_kit_inside_it.
    """
    found, claimed, seen = [], [], set()
    roots = [root] + ([brands] if brands.is_dir() else [])
    for start in roots:
        for dirpath, dirnames, _ in os.walk(start):
            dirnames[:] = sorted(d for d in dirnames if d not in SKIPPED_DIRS)
            d = Path(dirpath)
            resolved = d.resolve()
            if _under(resolved, claimed):
                dirnames[:] = []
                continue
            if resolved in seen:
                continue
            seen.add(resolved)
            if (d / "brand.py").is_file():
                claimed.append(resolved)
                dirnames[:] = []
                continue
            holds = system_holdings(d)
            if not holds:
                continue
            claimed.append(resolved)
            dirnames[:] = []
            found.append({"name": d.name, "path": _display(d, root), "holds": holds})
    return sorted(found, key=lambda r: (-system_strength(r["holds"]), r["name"]))


def verify_system(path):
    """The design system the user pointed at, checked and described.

    "The user pointed at it" is the strongest evidence there is, so this
    never overrules them: a directory with no recognisable markers is still
    reported and still recommended, with `holds` empty and a note saying so.
    What the check buys is the sentence that follows - either "these are the
    files a brand would be built from" or "nothing here looks like a token
    sheet; check the path".
    """
    path = Path(path).resolve()
    if not path.is_dir():
        return {"name": path.name, "path": str(path), "holds": [],
                "exists": False, "note": "no such directory"}
    holds = system_holdings(path)
    note = ("verified: %s" % ", ".join(holds)) if holds else (
        "no token sheet, tokens/ directory or _ds_manifest.json found here - "
        "the path is taken as given, but check it")
    return {"name": path.name, "path": str(path), "holds": holds,
            "exists": True, "note": note}


def recommend(brands, masters, systems=(), pointed=None):
    """One line the caller can act on.

    Candidate masters are not in the ranking. This pipeline starts from a
    design system and HTML examples; a .pptx on the machine is inventory.
    The argument stays in the signature because every caller passes it and
    because the report still lists what it found.
    """
    if pointed is not None:
        return ("use the design system you pointed at: %s - set a brand up "
                "from it (SKILL.md, Set up a brand)" % pointed["path"])
    real = [b["name"] for b in brands if "error" not in b]
    # The repository's own default is not evidence about the user's identity,
    # so it is ranked BELOW a design system found on disk. Any other brand
    # package is somebody's deliberate work and ranks above one.
    own = [n for n in real if n != DEFAULT_BRAND]
    if len(own) == 1:
        return "use brand %s" % own[0]
    if len(own) > 1:
        return "choose a brand: %s" % ", ".join(own)
    if systems:
        first = systems[0]
        return ("set up a brand from design system %s (%s): SKILL.md, "
                "Set up a brand" % (first["name"], first["path"]))
    if real:
        return "use brand %s" % real[0]
    return ("no design system of your own found: use the default, brands/%s"
            % DEFAULT_BRAND)


def discover(root, brands, design_system=None):
    brand_records = find_brands(brands)
    systems = find_systems(root, brands)
    masters = find_masters(root)
    pointed = verify_system(design_system) if design_system is not None else None
    return {
        "root": str(root),
        "brands_dir": str(brands),
        "pointed": pointed,
        "brands": brand_records,
        "systems": systems,
        "masters": masters,
        "tokens": find_tokens(root),
        "recommendation": recommend(brand_records, masters, systems, pointed),
    }


def _yes(flag):
    return "yes" if flag else "no"


def _master_lines(record):
    lines = ["  %s" % record["path"]]
    for master in record["masters"]:
        names = master["layouts"]
        shown = ", ".join(repr(n) for n in names[:LAYOUT_LIMIT])
        if len(names) > LAYOUT_LIMIT:
            shown += " (+%d more)" % (len(names) - LAYOUT_LIMIT)
        lines.append("    master %r: layouts %s" % (master["name"], shown))
    return lines


def render_masters(masters):
    """The candidate-master section, grouped by directory.

    A tree that keeps its build artifacts around holds one corporate
    template ninety times over, and printing each one's four masters and
    fifty layout names buries the only actionable line in the report under
    five hundred. A directory with more than MASTER_GROUP_LIMIT candidates
    is one line with a count.
    tests/test_discover.py::test_a_directory_of_many_masters_is_one_line_with_a_count.
    """
    lines = ["candidate masters (%d) - inventory, not a route: this pipeline "
             "builds from a design system" % len(masters)]
    groups = {}
    for record in masters:
        groups.setdefault(str(Path(record["path"]).parent), []).append(record)
    for directory in sorted(groups):
        records = groups[directory]
        if len(records) > MASTER_GROUP_LIMIT:
            lines.append("  %s: %d files, collapsed - e.g. %s"
                         % (directory, len(records), records[0]["path"]))
            continue
        for record in records:
            if "error" in record:
                lines.append("  %s: skipped, not readable - %s"
                             % (record["path"], record["error"]))
                continue
            lines += _master_lines(record)
    return lines


def render(report):
    rec = "recommendation: %s" % report["recommendation"]
    lines = [rec, "", "root: %s" % report["root"],
             "brands dir: %s" % report["brands_dir"], ""]
    pointed = report.get("pointed")
    if pointed is not None:
        lines.append("design system you pointed at")
        lines.append("  %s: %s" % (pointed["name"], pointed["note"]))
        lines.append("    path: %s" % pointed["path"])
        lines.append("")
    lines.append("brands (%d)" % len(report["brands"]))
    for b in report["brands"]:
        if "error" in b:
            lines.append("  %s: does not load - %s" % (b["name"], b["error"]))
        else:
            lines.append("  %s: master %r, layout %r" % (b["name"], b["master_name"],
                                                          b["layout_name"]))
        lines.append("    tokens.css %s, fonts/ %s, icons/ %s"
                     % (_yes(b["tokens_css"]), _yes(b["fonts"]), _yes(b["icons"])))
        for family, weight, filename in b.get("missing_fonts", []):
            lines.append("    MISSING FONT %s %s (%s): run "
                         "scripts/fetch_fonts.py --brand %s"
                         % (family, weight, filename, b["name"]))
    lines.append("")
    lines.append("design systems without a deckwright brand package (%d)"
                 % len(report["systems"]))
    for record in report["systems"]:
        lines.append("  %s: %s" % (record["name"], ", ".join(record["holds"])))
        lines.append("    path: %s" % record["path"])
    lines.append("")
    lines += render_masters(report["masters"])
    lines.append("")
    lines.append("tokens.css (%d)" % len(report["tokens"]))
    lines.extend("  %s" % t for t in report["tokens"])
    lines.append("")
    lines.append(rec)
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--root", type=Path, default=Path.cwd(),
                    help="tree to search for design systems and token sheets "
                         "(default: cwd)")
    ap.add_argument("--brands", type=Path, default=None,
                    help="brand packages dir (default: deck_kit.brand.brands_dir())")
    ap.add_argument("--design-system", type=Path, default=None,
                    help="the design system to build on, when the user has "
                         "one in mind: reported first, verified, recommended")
    ap.add_argument("--json", action="store_true", help="print the report as JSON")
    args = ap.parse_args(argv)

    root = args.root.resolve()
    if not root.is_dir():
        print("discover: no such root: %s" % args.root, file=sys.stderr)
        return 2
    if args.design_system is not None and not args.design_system.is_dir():
        print("discover: no such design system: %s" % args.design_system,
              file=sys.stderr)
        return 2
    brands = (args.brands if args.brands is not None else brands_dir()).resolve()
    report = discover(root, brands, args.design_system)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(render(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
