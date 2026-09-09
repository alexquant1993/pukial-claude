"""Diff two pptx packages part by part.

Exits 1 when they differ. Useful for two questions: what did that build step
actually change, and what did PowerPoint change when the author saved.

Run: uv run --offline --no-project --with python-pptx --with pillow \
       python scripts/diff_package.py old.pptx new.pptx
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from deck_kit.merge import read_package


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("a", type=Path)
    ap.add_argument("b", type=Path)
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    a, b = read_package(args.a), read_package(args.b)
    added = sorted(set(b) - set(a))
    removed = sorted(set(a) - set(b))
    changed = sorted(n for n in set(a) & set(b) if a[n] != b[n])
    same = len(set(a) & set(b)) - len(changed)

    print("added=%d removed=%d changed=%d identical=%d"
          % (len(added), len(removed), len(changed), same))
    if not args.quiet:
        for label, names in (("+", added), ("-", removed), ("~", changed)):
            for name in names:
                print("  %s %s" % (label, name))
    return 1 if (added or removed or changed) else 0


if __name__ == "__main__":
    sys.exit(main())
