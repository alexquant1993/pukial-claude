# Plantilla de workflow y test que la fija

Adaptada de pukial-flow (`.github/workflows/ci.yml` y `apps/web/test/ci-workflow.test.ts`). Cambia
los comandos, las rutas reincluidas y el runner; conserva la estructura.

## Workflow

```yaml
name: CI

# Reglas de minutos: docs/operations/ci.md. Las fija <ruta del test>.
on:
  push:
    branches: [main]
    paths:
      - '**'
      - '!**/*.md'
      - '!docs/**'
      # Documentos que lee el código o los tests: su cambio sí lanza el CI.
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
    # Añadir otra etiqueta no relanza la verificación.
    if: github.event.action != 'labeled' || github.event.label.name == 'ci-completo'
    # Runner propio con vuelta a GitHub por variable de repositorio (CI_RUNNER=github).
    runs-on: ${{ vars.CI_RUNNER == 'github' && 'ubuntu-24.04' || '<etiqueta-del-runner>' }}
    timeout-minutes: 60
    concurrency:
      group: ci-${{ github.event.pull_request.number || github.ref }}
      cancel-in-progress: ${{ github.event_name == 'pull_request' }}
    env:
      # Rápida en los PR; completa en main, a mano o con la etiqueta ci-completo.
      FULL_VERIFY: ${{ (github.event_name != 'pull_request' || contains(github.event.pull_request.labels.*.name, 'ci-completo')) && '1' || '0' }}
    steps:
      - uses: actions/checkout@v5
      # ... instalación con caché ...
      - run: ./scripts/verify   # lee FULL_VERIFY
```

Si los placeholders o enlaces de la documentación se validan, ponlos en un workflow aparte con
`paths: ['**/*.md', ...]`, que tarda segundos.

## Test (Vitest + `yaml`; tradúcelo al lenguaje del repo)

Lo esencial son tres comprobaciones:

1. `on.push.branches` es `['main']`, existe `pull_request`, y cada job tiene `concurrency`
   (grupo con el número de PR y `cancel-in-progress`) y `timeout-minutes` ≤ 60.
2. `push.paths` es igual a `pull_request.paths`, y unos ejemplos de rutas dan el resultado
   esperado (`README.md` no lanza; `Dockerfile` sí).
3. **El guardián:** recorrer el código y los tests, extraer las rutas de documentación que existen
   como archivo (`(?<![\w-])(?:docs|\.scratch)/[\w./-]+`; excluye el propio test) y exigir que
   cada una lance el CI según el filtro.

Evaluador del filtro, con la semántica de GitHub:

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

// Orden importa: un patrón positivo incluye, uno con ! excluye, uno positivo posterior reincluye.
function triggers(patterns: string[], path: string): boolean {
  let included = false
  for (const pattern of patterns) {
    const negative = pattern.startsWith('!')
    if (globToRegExp(negative ? pattern.slice(1) : pattern).test(path)) included = !negative
  }
  return included
}
```

El guardián encontró en pukial-flow 15 documentos que leen los tests (runbooks en
`docs/operations/`, capturas en `docs/definition/` y un YAML en `docs/research/`). Con un
`paths-ignore: '**/*.md'` ciego, cambiar cualquiera de ellos habría roto `main` sin pasar por el CI.

## Protección hermana: el Dockerfile

Si la imagen copia los `package.json` uno a uno antes de `install`, añade un test que exija un
`COPY` por cada paquete del workspace. Un paquete nuevo sin su `COPY` compila en local y en el CI
rápido, pero rompe la imagen (`TS2688: Cannot find type definition file for 'node'`).
