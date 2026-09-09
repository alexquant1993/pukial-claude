"""Out-of-process wrapper for the round trip's transplant stage.

Exists so the zip-surgery merge genuinely runs out of process, per
deck_kit.merge's own contract: a crash inside it cannot then corrupt an
in-memory Presentation, and the intermediate on disk stays openable.

The transplant, stated exactly: donor slide 1 lands at final position 5
(where the host's slide 5 was deleted), donor slide 2 lands at position 6
and is hidden.
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from deck_kit.merge import merge

ap = argparse.ArgumentParser()
ap.add_argument("--donor", required=True, type=Path)
ap.add_argument("inp", type=Path)
ap.add_argument("out", type=Path)
args = ap.parse_args()

merge(args.inp, args.donor, [(1, 5, False), (2, 6, True)], args.out, verbose=True)
