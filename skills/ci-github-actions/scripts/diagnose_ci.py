#!/usr/bin/env python3
"""Diagnose GitHub Actions usage for one repository or a whole account.

Run: python3 -I diagnose_ci.py OWNER/REPO [--runs 200] [--since YYYY-MM-DD] [--detail 5]
     python3 -I diagnose_ci.py OWNER [--runs 200] [--since YYYY-MM-DD]

Needs `gh` authenticated with read access to the repositories. Read-only: it changes nothing.

With OWNER alone (a user or an organization) it lists every private, non-archived repository and
prints one line each, heaviest first: minutes are shared across the account, so this shows which
repo is eating them. Public repositories are skipped because standard runners are free there.

With OWNER/REPO, for the most recent runs it shows:
  - how many there are per workflow, event, branch and result;
  - how many repeat a commit already tested (push + pull_request of the same SHA);
  - wall-clock duration (median and p90) and approximate minutes;
  - for the N most recent, the slowest steps of each job.

Minutes are wall-clock (created -> last updated): they include queue time and do not apply
per-job rounding or the macOS/Windows multipliers. Use them to compare and find the cause; the
billed number is in Settings -> Billing -> Usage.
"""

from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import subprocess
import sys


def gh(*args: str) -> object:
    out = subprocess.run(["gh", *args], capture_output=True, text=True)
    if out.returncode != 0:
        sys.exit(f"gh {' '.join(args)} failed:\n{out.stderr.strip()}")
    return json.loads(out.stdout or "null")


def ts(value: str | None) -> dt.datetime | None:
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00")) if value else None


def minutes(start: str | None, end: str | None) -> float:
    a, b = ts(start), ts(end)
    return (b - a).total_seconds() / 60 if a and b and b > a else 0.0


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(len(ordered) * p))]


def table(title: str, counter: collections.Counter, top: int = 8) -> None:
    print(f"\n{title}")
    for key, n in counter.most_common(top):
        print(f"  {n:5d}  {key}")


def load_runs(repo: str, limit: int, since: str | None) -> list[dict]:
    fields = "databaseId,workflowName,event,headBranch,headSha,conclusion,createdAt,updatedAt"
    runs = gh("run", "list", "-R", repo, "--limit", str(limit), "--json", fields) or []
    return [r for r in runs if r["createdAt"] >= since] if since else runs


def extra_runs(runs: list[dict]) -> tuple[int, list[int]]:
    """Commits tested more than once by the same workflow, and the indexes of the extra runs.

    Covers push + pull_request of the same SHA and repeated pushes. Runs are newest first: the
    oldest is the needed one, the rest are extra.
    """
    groups: dict[tuple[str, str], list[int]] = collections.defaultdict(list)
    for i, r in enumerate(runs):
        groups[(r["workflowName"], r["headSha"])].append(i)
    repeated = [idx for idx in groups.values() if len(idx) > 1]
    return len(repeated), [i for idx in repeated for i in idx[:-1]]


def report_account(owner: str, args: argparse.Namespace) -> None:
    repos = gh("repo", "list", owner, "--visibility", "private", "--no-archived", "--limit", "500",
               "--json", "nameWithOwner") or []
    if not repos:
        sys.exit(f"No private repositories visible for {owner}.")
    rows = []
    for repo in (r["nameWithOwner"] for r in repos):
        runs = load_runs(repo, args.runs, args.since)
        durations = [minutes(r["createdAt"], r["updatedAt"]) for r in runs]
        _, extra = extra_runs(runs)
        crons = sum(1 for r in runs if r["event"] == "schedule")
        failed = sum(1 for r in runs if r["conclusion"] == "failure")
        rows.append((sum(durations), sum(durations[i] for i in extra), len(runs), crons, failed, repo))
    rows.sort(reverse=True)
    total = sum(row[0] for row in rows)
    window = f"since {args.since}" if args.since else f"last {args.runs} runs per repo"
    active = sum(1 for row in rows if row[2])
    print(f"Account {owner}: {len(rows)} private repos, {active} with runs ({window}), "
          f"~{total:.0f} wall-clock min in all")
    print(f"\n  {'~min':>6} {'share':>6} {'extra':>6} {'runs':>5} {'cron':>5} {'fail':>5}  repo")
    for mins, extra_mins, n, crons, failed, repo in rows:
        if not n:
            continue
        print(f"  {mins:6.0f} {100 * mins / max(total, 1):5.0f}% {extra_mins:6.0f} {n:5d} {crons:5d} {failed:5d}  {repo}")
    print('\n"extra" = minutes spent re-testing a commit already tested. "cron" runs are the ones that stop\n'
          "first when the quota runs out. Next: run this script with OWNER/REPO on the heaviest repo.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("target", help="OWNER/REPO for one repository, or OWNER for every private repo")
    parser.add_argument("--runs", type=int, default=200, help="runs to read per repo (max 1000)")
    parser.add_argument("--since", help="only runs created on or after this date (YYYY-MM-DD)")
    parser.add_argument("--detail", type=int, default=5, help="recent runs to break down by step")
    args = parser.parse_args()

    if "/" not in args.target:
        report_account(args.target, args)
        return
    args.repo = args.target

    runs = load_runs(args.repo, args.runs, args.since)
    if not runs:
        sys.exit("No runs in the requested range.")

    info = gh("repo", "view", args.repo, "--json", "visibility,defaultBranchRef") or {}
    default_branch = (info.get("defaultBranchRef") or {}).get("name") or "main"
    print(f"Repository {args.repo} ({info.get('visibility', '?')}): {len(runs)} runs, "
          f"{runs[-1]['createdAt'][:10]} -> {runs[0]['createdAt'][:10]}")
    if info.get("visibility") == "PUBLIC":
        print("  Public repository: standard GitHub-hosted runners do not use minutes.")

    durations = [minutes(r["createdAt"], r["updatedAt"]) for r in runs]
    by_workflow: dict[str, float] = collections.defaultdict(float)
    for r, m in zip(runs, durations):
        by_workflow[r["workflowName"]] += m
    print(f"\nWall-clock minutes: total ~{sum(durations):.0f}; median {percentile(durations, 0.5):.1f}, "
          f"p90 {percentile(durations, 0.9):.1f} per run")
    for name, m in sorted(by_workflow.items(), key=lambda kv: -kv[1]):
        print(f"  ~{m:6.0f} min  {name}")

    table("By event", collections.Counter(r["event"] for r in runs))
    table("By branch", collections.Counter(r["headBranch"] or "?" for r in runs))
    table("By result", collections.Counter(r["conclusion"] or "in progress" for r in runs))

    repeated, extra = extra_runs(runs)
    extra_minutes = sum(durations[i] for i in extra)
    print(f"\nCommits tested more than once: {repeated}; "
          f"extra runs {len(extra)} (~{extra_minutes:.0f} min, "
          f"{100 * extra_minutes / max(sum(durations), 1):.0f} %)")

    events = collections.Counter(r["event"] for r in runs)
    if events["push"] and events["pull_request"]:
        push_branches = {r["headBranch"] for r in runs if r["event"] == "push"}
        if push_branches - {default_branch}:
            print(f"  Warning: push runs on branches other than {default_branch} and pull_request runs too: "
                  "every commit with an open PR is tested twice.")

    if args.detail:
        print(f"\nSlowest steps in the {args.detail} most recent finished runs:")
        finished = [r for r in runs if r["conclusion"]][: args.detail]
        for r in finished:
            data = gh("run", "view", str(r["databaseId"]), "-R", args.repo, "--json", "jobs") or {}
            for job in data.get("jobs", []):
                steps = sorted(
                    ((minutes(s.get("startedAt"), s.get("completedAt")), s["name"]) for s in job.get("steps", [])),
                    reverse=True,
                )[:4]
                total = minutes(job.get("startedAt"), job.get("completedAt"))
                print(f"  {r['createdAt'][:16]} {r['event']:<12} {job['name'][:30]:<30} {total:5.1f} min · "
                      + "; ".join(f"{n[:28]} {m:.1f}" for m, n in steps))

    print("\nNext step: compare against the skill's rules (SKILL.md, \"Rules\").")


if __name__ == "__main__":
    main()
