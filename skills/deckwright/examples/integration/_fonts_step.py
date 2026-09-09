"""Out-of-process wrapper for the round trip's font-transplant stage.

Exists so the font splice genuinely runs out of process, matching the
merge stage's own rationale. `--expect` is required and asserted exactly by
`fonts.transplant` itself - a donor that lost a face must stop the build.
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from deck_kit.fonts import transplant

ap = argparse.ArgumentParser()
ap.add_argument("--donor", required=True, type=Path)
ap.add_argument("--expect", required=True, type=int)
ap.add_argument("inp", type=Path)
ap.add_argument("out", type=Path)
args = ap.parse_args()

transplant(args.inp, args.donor, args.out, expect_parts=args.expect)
