# Workflow template and the test that pins it

Change the commands, the re-included paths and the runner; keep the structure.

## Workflow

```yaml
name: CI

# Minutes rules: docs/operations/ci.md. Pinned by <path to the test>.
on:
  push:
    branches: [main]
    paths:
      - '**'
      - '!**/*.md'
      - '!docs/**'
      # Docs the code or tests read: changing them does run the CI.
      - 'docs/operations/**'
  pull_request:
    types: [opened, synchronize, reopened, labeled]
    paths:
      - '**'
      - '!**/*.md'
      - '!docs/**'
      - 'docs/operations/**'
  workflow_dispatch:

jobs:
  verify:
    # Adding any other label does not restart the verification.
    if: github.event.action != 'labeled' || github.event.label.name == 'full-ci'
    # Self-hosted runner, with a switch back to GitHub-hosted via a repo variable (CI_RUNNER=github).
    # Without a self-hosted runner, just use: runs-on: ubuntu-24.04
    runs-on: ${{ vars.CI_RUNNER == 'github' && 'ubuntu-24.04' || '<runner-label>' }}
    timeout-minutes: 60
    concurrency:
      group: ci-${{ github.event.pull_request.number || github.ref }}
      cancel-in-progress: ${{ github.event_name == 'pull_request' }}
    env:
      # Fast on PRs; full on main, on demand, or with the full-ci label.
      FULL_VERIFY: ${{ (github.event_name != 'pull_request' || contains(github.event.pull_request.labels.*.name, 'full-ci')) && '1' || '0' }}
    steps:
      - uses: actions/checkout@v5
      # ... install with cache ...
      - run: ./scripts/verify   # reads FULL_VERIFY
```

If `verify` is a required status check, read "Required checks and path filters" in `SKILL.md`
before adding `paths`.

If docs placeholders or links are validated, put that in a separate workflow with
`paths: ['**/*.md', ...]`; it takes seconds.

## Test (Vitest + `yaml` here; translate it to the repo's language)

Three checks matter:

1. `on.push.branches` is `['main']`, `pull_request` exists, and every job has `concurrency` (group
   with the PR number and `cancel-in-progress`) and `timeout-minutes` ≤ 60.
2. `push.paths` equals `pull_request.paths`, and a few sample paths give the expected result
   (`README.md` does not trigger; `Dockerfile` does).
3. **The guard:** walk the code and tests, extract the docs paths that exist as files
   (`(?<![\w-])docs/[\w./-]+`, plus any other docs roots the repo uses; skip the test itself), and
   require that each one triggers the CI under the filter.

Filter evaluator, with GitHub's semantics:

```ts
function globToRegExp(glob: string): RegExp {
  let source = ''
  for (let i = 0; i < glob.length; i++) {
    if (glob.startsWith('**/', i)) { source += '(?:.*/)?'; i += 2 }
    else if (glob.startsWith('**', i)) { source += '.*'; i += 1 }
    else if (glob[i] === '*') source += '[^/]*'
    else source += glob[i].replace(/[.+?^${}()|[\]\\]/g, '\\$&')
  }
  return new RegExp(`^${source}$`)
}

// Order matters: a positive pattern includes, a ! pattern excludes, a later positive re-includes.
function triggers(patterns: string[], path: string): boolean {
  let included = false
  for (const pattern of patterns) {
    const negative = pattern.startsWith('!')
    if (globToRegExp(negative ? pattern.slice(1) : pattern).test(path)) included = !negative
  }
  return included
}
```

On a mid-sized monorepo the guard can find a dozen or more docs files that tests read (runbooks,
fixture screenshots, YAML definitions kept under `docs/`). With a blind `paths-ignore: '**/*.md'`,
changing any of them would break `main` without going through CI.

## Sibling guard: the Dockerfile

If the image copies each `package.json` one by one before `install`, add a test that requires one
`COPY` per workspace package. A new package without its `COPY` builds locally and in the fast CI
but breaks the image (e.g. `TS2688: Cannot find type definition file for 'node'`).
