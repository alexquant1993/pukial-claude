"""Fetch a brand's declared type families, OFL only, hash-pinned.

A brand names the faces its design system asks for. Until this script
existed, a face nobody had on disk was silently replaced by whatever OFL
file the repository already carried, and the substitution then had to be
argued for in a README - which is how `brands/relay` came to measure Space
Grotesk, Public Sans and JetBrains Mono against Noto Sans. Fetching is the
better answer whenever the face is OFL, because all three of those are.

**Only OFL faces are fetched.** A proprietary face is pointed at by name
in `brand.py` and never copied into the repository, so this script refuses
any manifest entry whose `licence` is not the SIL Open Font License 1.1.
That is not a stylistic preference: committing a proprietary binary is a
licence violation, and a fetcher that could do it would make the violation
one line of TOML away.

## The manifest

`brands/<name>/fonts.toml`, a sibling of `assets.toml`. Two files rather
than one, because `scripts/lint_deck.py manifest --brand <name>`
regenerates `assets.toml` wholesale from what is on disk and would drop any
`[[font]]` block written into it. `assets.toml` says where a committed
binary came from; `fonts.toml` says what to fetch and how to know it is the
right bytes. A fetched face appears in BOTH: this script writes it into
`fonts/`, and the human then records it in `assets.toml` like every other
binary.

One `[[font]]` block per face:

    [[font]]
    family      = "Space Grotesk"     # the family name a builder writes into the PPTX
    role        = "display"           # display | sans | mono
    weight      = "regular"           # regular | bold
    file        = "SpaceGrotesk-Regular.ttf"   # the name inside fonts/
    url         = "https://raw.githubusercontent.com/.../SpaceGrotesk-Regular.ttf"
    sha256      = ""                  # empty on the first fetch; see below
    licence     = "SIL Open Font License 1.1"
    licence_url = "https://raw.githubusercontent.com/.../OFL.txt"
    licence_file = "SpaceGrotesk-OFL.txt"      # written next to the face

`sha256` is empty exactly once. The first run downloads the file, prints
the hash it got, and writes the face; a human pastes that hash into the
manifest. Every run after that verifies against it and REFUSES a file whose
bytes moved - it neither writes the download nor touches what is on disk.
An empty hash is a one-time state, not a mode: leaving it empty means every
run re-downloads and nothing is pinned, and `--check` says so.

A face already on disk whose hash matches is never re-downloaded and never
rewritten. Re-running this script on a clean tree touches nothing.

## What it does not do

It does not install the face on the machine. `deck_kit.metrics` measures
against the file in `fonts/`, so a build and its wrap simulation are
correct with nothing installed - but PowerPoint renders with the fonts
Windows knows about, so an export on a machine where the family is not
installed shows a substitute. `references/03-pptx-stage.md` says what that
costs and how to install per user.

Run:
  uv run --offline --no-project --with python-pptx --with pillow \\
    python scripts/fetch_fonts.py --brand relay
  ... --brand relay --check      # report only, no network, exit 1 if short
  ... --brand relay --dry-run    # say what would be fetched, fetch nothing

Exit 0 when every declared face is present and pinned, 1 on a refusal (a
hash that moved, a licence that is not OFL, a malformed manifest, a
`--check` that came up short), 2 when the brand or its manifest is missing.
"""

import argparse
import hashlib
import sys
import tomllib
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from deck_kit.brand import brands_dir  # noqa: E402

MANIFEST_NAME = "fonts.toml"
ROLES = ("display", "sans", "mono")
WEIGHTS = ("regular", "bold")
# The one licence a face may be committed under. OFL 1.1 permits
# redistribution with the licence text alongside, which is why every entry
# also carries a licence_url this script writes next to the face.
OFL = "SIL Open Font License 1.1"
REQUIRED = ("family", "role", "weight", "file", "url", "licence",
            "licence_url", "licence_file")
TIMEOUT = 60


class ManifestError(Exception):
    """The manifest is not something this script will act on."""


class FetchRefused(Exception):
    """The bytes are not the bytes the manifest pinned."""


def fetch_bytes(url):
    """Download `url`. The one function that touches the network.

    A module-level function rather than an inline urlopen so a test can
    replace it: nothing in tests/ may reach the network, and a fetcher whose
    only test is "it downloaded something" tests the network rather than the
    fetcher.
    """
    with urllib.request.urlopen(url, timeout=TIMEOUT) as response:
        return response.read()


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def _validate(entry, index, where):
    """One `[[font]]` block, checked field by field, or raise.

    Every refusal here is a refusal to write a file. `file` and
    `licence_file` are checked for path separators because they name a
    destination inside `fonts/`, and "../../brands/other/fonts/x.ttf" is a
    manifest that overwrites another brand's faces.
    """
    if not isinstance(entry, dict):
        raise ManifestError("%s: entry %d is not a table" % (where, index))
    for field in REQUIRED:
        if not isinstance(entry.get(field), str) or not entry[field].strip():
            raise ManifestError("%s: entry %d needs a non-empty string %s"
                                % (where, index, field))
    if entry["role"] not in ROLES:
        raise ManifestError("%s: entry %d role %r is not one of %s"
                            % (where, index, entry["role"], ", ".join(ROLES)))
    if entry["weight"] not in WEIGHTS:
        raise ManifestError("%s: entry %d weight %r is not one of %s"
                            % (where, index, entry["weight"], ", ".join(WEIGHTS)))
    if entry["licence"] != OFL:
        raise ManifestError(
            "%s: entry %d licence %r - only %r may be fetched and committed; a "
            "proprietary face is pointed at in brand.py, never copied"
            % (where, index, entry["licence"], OFL))
    for field in ("url", "licence_url"):
        if not entry[field].startswith("https://"):
            raise ManifestError("%s: entry %d %s must be https"
                                % (where, index, field))
    for field in ("file", "licence_file"):
        name = entry[field]
        if Path(name).name != name or name in (".", ".."):
            raise ManifestError("%s: entry %d %s must be a bare filename, not %r"
                                % (where, index, field, name))
    pinned = entry.get("sha256", "")
    if not isinstance(pinned, str):
        raise ManifestError("%s: entry %d sha256 must be a string" % (where, index))
    if pinned and len(pinned) != 64:
        raise ManifestError("%s: entry %d sha256 is not a 64-character digest"
                            % (where, index))
    return dict(entry, sha256=pinned)


def read_manifest(brand_dir):
    """The `[[font]]` blocks of `brand_dir/fonts.toml`, validated.

    An absent manifest is [] and not an error: most brands declare no faces
    to fetch, and `discover.py` asks every brand this question.
    """
    path = Path(brand_dir) / MANIFEST_NAME
    if not path.is_file():
        return []
    with open(path, "rb") as fh:
        data = tomllib.load(fh)
    entries = data.get("font", [])
    if not isinstance(entries, list):
        raise ManifestError("%s: [[font]] must be a list of tables" % path)
    seen, out = set(), []
    for i, entry in enumerate(entries):
        checked = _validate(entry, i, str(path))
        if checked["file"] in seen:
            raise ManifestError("%s: file %s declared twice" % (path, checked["file"]))
        seen.add(checked["file"])
        out.append(checked)
    return out


def face_status(brand_dir, entry):
    """One of "ok", "missing", "unpinned", "mismatch" for one declared face.

    unpinned: the file is there but the manifest pins no hash, so nothing
    says these are the bytes anyone reviewed. It is a state to leave, not a
    state to live in, which is why --check treats it as short.
    """
    path = Path(brand_dir) / "fonts" / entry["file"]
    if not path.is_file():
        return "missing"
    if not entry["sha256"]:
        return "unpinned"
    return "ok" if sha256(path.read_bytes()) == entry["sha256"] else "mismatch"


def missing_fonts(brand_dir):
    """[(family, weight, file)] for every declared face not on disk.

    What `scripts/discover.py` reports per brand, so the intake can say "run
    fetch_fonts.py" before a builder measures against a face that is not
    there. A manifest this script would refuse is reported as one entry
    naming the error rather than raising into the intake report.
    """
    try:
        entries = read_manifest(brand_dir)
    except (ManifestError, tomllib.TOMLDecodeError) as exc:
        return [("%s: %s" % (MANIFEST_NAME, exc), "", "")]
    return [(e["family"], e["weight"], e["file"]) for e in entries
            if face_status(brand_dir, e) == "missing"]


def _write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def fetch_one(brand_dir, entry, out=None, dry_run=False):
    """Fetch one face and its licence. Returns the status word for the report.

    "ok" means the file on disk already matches the pinned hash: nothing is
    downloaded and nothing is written. That is the ordinary case on a clean
    tree, and it is what makes this script safe to run on every intake.
    """
    out = sys.stdout if out is None else out
    fonts = Path(brand_dir) / "fonts"
    target = fonts / entry["file"]
    status = face_status(brand_dir, entry)
    if status == "ok":
        print("  ok        %s" % entry["file"], file=out)
        return "ok"
    if status == "mismatch":
        raise FetchRefused(
            "%s: on disk sha256 %s, manifest pins %s - refusing to overwrite. "
            "Delete the file to re-fetch, or fix the manifest."
            % (entry["file"], sha256(target.read_bytes())[:16] + "...",
               entry["sha256"][:16] + "..."))
    if dry_run:
        print("  would fetch %s from %s" % (entry["file"], entry["url"]), file=out)
        return status
    if status == "unpinned" and target.is_file():
        # Already downloaded once, never pinned. Re-downloading would prove
        # nothing (there is no hash to compare against) and would overwrite
        # bytes a human may already have looked at.
        print("  UNPINNED  %s  sha256 = %r  <- paste into %s"
              % (entry["file"], sha256(target.read_bytes()), MANIFEST_NAME), file=out)
        return "unpinned"

    data = fetch_bytes(entry["url"])
    got = sha256(data)
    if entry["sha256"] and got != entry["sha256"]:
        raise FetchRefused(
            "%s: downloaded sha256 %s, manifest pins %s - nothing written"
            % (entry["file"], got, entry["sha256"]))
    _write(target, data)
    _write(fonts / entry["licence_file"], fetch_bytes(entry["licence_url"]))
    if entry["sha256"]:
        print("  fetched   %s  (%d bytes, hash verified)" % (entry["file"], len(data)),
              file=out)
        return "fetched"
    print("  fetched   %s  (%d bytes, NOT PINNED)" % (entry["file"], len(data)), file=out)
    print("            sha256 = %r  <- paste into %s" % (got, MANIFEST_NAME), file=out)
    return "unpinned"


def run(brand_dir, out=None, dry_run=False, check=False):
    """Every declared face for one brand. Returns the process exit code.

    `out` is resolved here rather than defaulted to `sys.stdout` in the
    signature: a default argument binds the stream at import, which is a
    different object from the one a test - or a caller redirecting output -
    installs later.
    """
    out = sys.stdout if out is None else out
    entries = read_manifest(brand_dir)
    if not entries:
        print("%s declares no fonts to fetch (no %s)" % (brand_dir, MANIFEST_NAME),
              file=out)
        return 0
    print("%s: %d declared face(s)" % (brand_dir, len(entries)), file=out)
    short = []
    for entry in entries:
        if check:
            # --check asks whether the tree is settled, so a face this run
            # would have downloaded is still short. Only "ok" passes.
            status = face_status(brand_dir, entry)
            print("  %-9s %s" % (status, entry["file"]), file=out)
            ready = status == "ok"
        else:
            status = fetch_one(brand_dir, entry, out=out, dry_run=dry_run)
            ready = status in ("ok", "fetched")
        if not ready:
            short.append("%s (%s)" % (entry["file"], status))
    if short:
        print("", file=out)
        print("not ready: %s" % ", ".join(short), file=out)
        return 1
    print("", file=out)
    print("every declared face is present and matches its pinned hash", file=out)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--brand", required=True, help="brand package name")
    ap.add_argument("--brands", type=Path, default=None,
                    help="brand packages dir (default: deck_kit.brand.brands_dir())")
    ap.add_argument("--check", action="store_true",
                    help="report status only; touch no network and write nothing")
    ap.add_argument("--dry-run", action="store_true",
                    help="say what would be fetched, fetch nothing")
    args = ap.parse_args(argv)

    root = args.brands if args.brands is not None else brands_dir()
    brand_dir = Path(root) / args.brand
    if not brand_dir.is_dir():
        print("fetch_fonts: no such brand: %s (looked in %s)" % (args.brand, root),
              file=sys.stderr)
        return 2
    try:
        return run(brand_dir, dry_run=args.dry_run, check=args.check)
    except (ManifestError, FetchRefused, tomllib.TOMLDecodeError) as exc:
        print("fetch_fonts: %s" % exc, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
