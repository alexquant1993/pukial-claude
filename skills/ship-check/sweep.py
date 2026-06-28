#!/usr/bin/env python3
"""
/ship-check — Stage 0.5 deterministic TIER-1 grep sweep.

Loads tier1-rules.yaml, runs each rule's regex over the working tree, and
partitions every hit into:
  - "in_diff"     : the hit's line falls in an added/modified hunk of
                    `git diff --unified=0 <BASE_SHA>` (base -> WORKING TREE, no ..HEAD),
                    so brand-new uncommitted violations and fix-loop edits both register.
  - "pre_existing": everywhere else -> the advisory "existing drift" baseline.

Honors inline `// ship-check:ignore <rule-id>` (same line or the line above).
Zero runtime dependencies: uses PyYAML if importable, else a tiny built-in reader
(the rules file is authored with strict-JSON values, a valid YAML subset).

Exit code: 0 if no in-diff Critical/Important findings, 1 otherwise. (Pre-existing
drift and minor/in-diff-minor never set a failing code — the maturity guard.)
"""
import argparse
import functools
import json
import os
import re
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------- rule loading


def _load_rules_pyyaml(text):
    import yaml  # type: ignore
    return yaml.safe_load(text)


def _load_rules_minimal(text):
    # Minimal reader for this file's shape: a `version:` scalar and a `rules:`
    # list of mappings whose every value is strict JSON (so json.loads handles
    # all escaping in the regex patterns and the glob arrays).
    # NOTE: only FULL-LINE `#` comments are stripped — we never strip inline, so a
    # `#` inside a quoted JSON value (e.g. a future hex-colour pattern) is preserved.
    doc = {"version": None, "rules": []}
    cur = None
    for raw in text.splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("version:"):
            doc["version"] = json.loads(stripped.split(":", 1)[1].strip())
            continue
        if stripped == "rules:":
            continue
        if stripped.startswith("- "):
            if cur:
                doc["rules"].append(cur)
            cur = {}
            stripped = stripped[2:].strip()
        if cur is None:
            continue
        key, _, val = stripped.partition(":")
        cur[key.strip()] = json.loads(val.strip())
    if cur:
        doc["rules"].append(cur)
    return doc


def load_rules(path):
    text = Path(path).read_text(encoding="utf-8")
    try:
        doc = _load_rules_pyyaml(text)
    except Exception:
        try:
            doc = _load_rules_minimal(text)
        except Exception as e:
            raise SystemExit(
                f"ship-check: could not parse {path} without PyYAML ({e}).\n"
                f"  Fix: `pip3 install pyyaml`, OR ensure every value is single-line "
                f"strict JSON and only full-line comments start with '#'."
            )
    rules = []
    for r in doc.get("rules", []):
        rules.append(
            {
                "id": r["id"],
                "severity": r.get("severity", "important"),
                "message": r.get("message", ""),
                "regex": re.compile(r["pattern"]),
                "include": r.get("include", ["lib/**/*.dart"]),
                "exclude": r.get("exclude", []),
            }
        )
    return doc.get("version"), rules


# ---------------------------------------------------------------- globbing


@functools.lru_cache(maxsize=None)
def glob_to_regex(glob):
    # Supports **, *, ? with / as a path separator. ** spans directories.
    # Cached: matches_any is called rules×files×globs times.
    i, out = 0, ["^"]
    while i < len(glob):
        c = glob[i]
        if glob[i : i + 2] == "**":
            out.append(".*")
            i += 2
            if i < len(glob) and glob[i] == "/":
                i += 1  # `**/` also matches zero dirs
        elif c == "*":
            out.append("[^/]*")
            i += 1
        elif c == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(c))
            i += 1
    out.append("$")
    return re.compile("".join(out))


def matches_any(relpath, globs):
    return any(glob_to_regex(g).match(relpath) for g in globs)


# ---------------------------------------------------------------- git / diff


def run_git(args, root):
    return subprocess.run(
        ["git", *args], cwd=root, capture_output=True, text=True
    )


def resolve_base_sha(root, override):
    if override:
        return override, "explicit"
    chains = [
        (["merge-base", "HEAD", "origin/main"], "merge-base origin/main"),
        (["merge-base", "HEAD", "main"], "merge-base main"),
        (["rev-parse", "HEAD~1"], "HEAD~1"),
    ]
    for args, label in chains:
        res = run_git(args, root)
        sha = res.stdout.strip()
        if res.returncode == 0 and sha:
            return sha, label
    return "", "none (first commit / shallow) — whole tree treated as in-diff"


def added_line_ranges(base, root):
    # base -> WORKING TREE (no ..HEAD): includes staged + unstaged changes.
    # `git diff` does NOT show untracked files, so we fold them in separately and
    # mark them wholly in-diff (sentinel True) — otherwise a brand-new file (incl.
    # one the fix agent creates, e.g. AppImages) would misclassify as pre-existing
    # drift and the loop could converge "clean" while shipping new violations.
    if not base:
        return None  # signal: treat everything as in-diff
    ranges = {}
    cur = None
    res = run_git(["diff", "--unified=0", base], root)
    for line in res.stdout.splitlines():
        if line.startswith("+++ "):
            p = line[4:].strip()
            cur = None if p == "/dev/null" else p[2:] if p.startswith("b/") else p
            if cur is not None:
                ranges.setdefault(cur, [])
        elif line.startswith("@@") and cur is not None:
            m = re.search(r"\+(\d+)(?:,(\d+))?", line)
            if not m:
                continue
            start = int(m.group(1))
            count = int(m.group(2)) if m.group(2) is not None else 1
            if count > 0:
                ranges[cur].append((start, start + count - 1))
    # Untracked, non-ignored files -> entire contents are new work.
    untracked = run_git(["ls-files", "--others", "--exclude-standard"], root)
    for p in untracked.stdout.splitlines():
        if p.strip():
            ranges[p.strip()] = True  # sentinel: whole file in-diff
    return ranges


def is_in_diff(ranges, relpath, lineno):
    if ranges is None:
        return True  # no base -> everything actionable
    r = ranges.get(relpath)
    if r is True:  # untracked / whole-file-new
        return True
    if not r:
        return False
    return any(start <= lineno <= end for start, end in r)


# ---------------------------------------------------------------- suppression

_IGNORE = re.compile(r"ship-check:ignore\s+([a-z0-9-]+)")


def suppressed(rule_id, lines, idx):
    # idx is 0-based. A directive suppresses:
    #   - the SAME line (trailing comment), always; or
    #   - the line ABOVE, but only if that line is comment-only (a standalone
    #     `// ship-check:ignore <id>` above the violation) — so a trailing-comment
    #     directive does not bleed onto the next line.
    if rule_id in _IGNORE.findall(lines[idx]):
        return True
    if idx - 1 >= 0:
        above = lines[idx - 1].strip()
        if above.startswith("//") and rule_id in _IGNORE.findall(above):
            return True
    return False


# ---------------------------------------------------------------- scan


def discover_files(root, globs):
    # Walk the top dirs named by the globs and return every file; matches_any()
    # then filters by the full glob (extension included). Generic over extension,
    # so a future .arb/.yaml rule is not silently skipped.
    seen = set()
    for top in {g.split("/", 1)[0] for g in globs}:
        base = Path(root) / top
        if base.is_dir():
            for p in base.rglob("*"):
                if p.is_file():
                    seen.add(str(p.relative_to(root)))
    return sorted(seen)


def scan(root, version, rules):
    findings, suppress_count = [], 0
    # Pre-discover candidate files per unique include set.
    for rule in rules:
        for relpath in discover_files(root, rule["include"]):
            if not matches_any(relpath, rule["include"]):
                continue
            if matches_any(relpath, rule["exclude"]):
                continue
            try:
                lines = (Path(root) / relpath).read_text(
                    encoding="utf-8", errors="replace"
                ).splitlines()
            except OSError:
                continue
            for idx, text in enumerate(lines):
                if rule["regex"].search(text):
                    if suppressed(rule["id"], lines, idx):
                        suppress_count += 1
                        continue
                    findings.append(
                        {
                            "rule": rule["id"],
                            "severity": rule["severity"],
                            "message": rule["message"],
                            "file": relpath,
                            "line": idx + 1,
                            "text": text.strip()[:160],
                        }
                    )
    return findings, suppress_count


# ---------------------------------------------------------------- report


def build_report(root, base, base_label, ranges, findings, suppress_count, version):
    for f in findings:
        f["scope"] = "in_diff" if is_in_diff(ranges, f["file"], f["line"]) else "pre_existing"
    in_diff = [f for f in findings if f["scope"] == "in_diff"]
    pre = [f for f in findings if f["scope"] == "pre_existing"]
    blocking = [f for f in in_diff if f["severity"] in ("critical", "important")]
    drift_by_rule = {}
    for f in pre:
        drift_by_rule.setdefault(f["rule"], 0)
        drift_by_rule[f["rule"]] += 1
    return {
        "version": version,
        "base_sha": base,
        "base_resolution": base_label,
        "suppressed": suppress_count,
        "counts": {
            "in_diff": len(in_diff),
            "in_diff_blocking": len(blocking),
            "pre_existing": len(pre),
        },
        "in_diff": in_diff,
        "existing_drift": {"by_rule": drift_by_rule, "items": pre},
        "passed": len(blocking) == 0,
    }


def print_human(rep):
    print("── /ship-check · Stage 0.5 TIER-1 sweep ──")
    print(f"  standard version : {rep['version']}")
    print(f"  base             : {rep['base_sha'] or '(none)'}  [{rep['base_resolution']}]")
    print(f"  suppressed       : {rep['suppressed']} (// ship-check:ignore)")
    print()
    print(f"YOUR CHANGES — {rep['counts']['in_diff']} finding(s), "
          f"{rep['counts']['in_diff_blocking']} blocking:")
    if not rep["in_diff"]:
        print("  (clean)")
    for f in sorted(rep["in_diff"], key=lambda x: (x["severity"], x["file"])):
        print(f"  [{f['severity'].upper():9}] {f['file']}:{f['line']}  {f['rule']}")
        print(f"             {f['text']}")
    print()
    drift = rep["existing_drift"]
    print(f"EXISTING DRIFT (advisory, never blocks) — {rep['counts']['pre_existing']} hit(s):")
    if not drift["by_rule"]:
        print("  (none)")
    for rule, n in sorted(drift["by_rule"].items(), key=lambda kv: -kv[1]):
        print(f"  {n:4}×  {rule}")
    print()
    print("RESULT:", "PASS" if rep["passed"] else "FAIL (in-diff Critical/Important present)")


# ---------------------------------------------------------------- main


def main():
    ap = argparse.ArgumentParser(description="ship-check TIER-1 sweep")
    here = Path(__file__).resolve().parent
    ap.add_argument("--root", default=os.getcwd(), help="repo root (default: cwd)")
    ap.add_argument("--rules", default=str(here / "tier1-rules.yaml"))
    ap.add_argument("--base", default="", help="override BASE_SHA")
    ap.add_argument("--json", default="", help="also write the JSON report to this path")
    ap.add_argument("--format", choices=["human", "json"], default="human")
    args = ap.parse_args()

    version, rules = load_rules(args.rules)
    base, base_label = resolve_base_sha(args.root, args.base)
    ranges = added_line_ranges(base, args.root)
    findings, suppress_count = scan(args.root, version, rules)
    rep = build_report(args.root, base, base_label, ranges, findings, suppress_count, version)

    if args.json:
        Path(args.json).write_text(json.dumps(rep, indent=2), encoding="utf-8")
    if args.format == "json":
        print(json.dumps(rep, indent=2))
    else:
        print_human(rep)
    return 0 if rep["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
