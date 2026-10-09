---
name: ci-github-actions
description: >-
  Diseña, revisa y repara el CI de GitHub Actions de cualquier proyecto de Pukial para que no
  agote los minutos de la cuenta ni deje parados otros repositorios. Úsala SIEMPRE que crees o
  edites un archivo en .github/workflows/, cuando un workflow tarde mucho o se ejecute de más,
  cuando GitHub avise de minutos o presupuesto agotados, cuando un workflow programado (cron)
  deje de ejecutarse sin motivo aparente, o al montar un runner propio (self-hosted) en el R620
  u otra máquina. Trigger: "CI", "GitHub Actions", "workflow", "minutos de GitHub", "se acabaron
  los minutos", "spending limit", "self-hosted runner", "el CI tarda", "el cron de GitHub no
  corre". No la uses para depurar un test concreto que falla (eso es depuración normal) ni para
  CI que no sea GitHub Actions.
---

# CI en GitHub Actions sin quemar la cuenta

Los minutos y el presupuesto de Actions son **de la cuenta, no del repositorio**. Cuando un repo
los agota, GitHub para **todos** los workflows privados de esa cuenta, también los programados de
otros productos. Precedente (octubre de 2026): el CI de pukial-flow consumió ~2.300 de los 2.000
minutos gratis y los 12 USD de presupuesto. El motor SEO de Waki (crons en `waki-web`) se quedó sin
botones de Telegram ni artículos, y además `main` llevaba un fallo real que nadie vio por el ruido.

## Flujo

1. **Medir antes de opinar.** Ejecuta el diagnóstico y lee el resultado:
   `python3 -I scripts/diagnostico-ci.py OWNER/REPO --runs 200`
   Da las ejecuciones por evento, rama y resultado, los commits probados más de una vez y los pasos
   más lentos. Si hay varios repos en la cuenta, ejecútalo en todos: el problema es la suma.
2. **Si los minutos ya están agotados**, sigue `references/emergencia.md` antes que nada: primero se
   reactiva lo que da servicio a usuarios, después se arregla el CI.
3. **Contrasta el workflow con las reglas** (abajo). Cada regla incumplida es un cambio concreto.
4. **Fija las reglas con un test** que lea el YAML: un workflow sin test vuelve a degradarse en la
   siguiente edición. Plantilla y test de ejemplo en `references/plantilla-workflow.md`.
5. **Mira si `main` está en rojo** por un fallo real, no por los minutos. Arréglalo con un test que
   lo habría detectado.
6. **Runner propio** solo si, aplicadas las reglas, el CI sigue sin caber en el plan, o si hay
   automatizaciones críticas que no deben depender de la cuota: `references/runner-propio.md`.
7. **Documenta en el repo** (runbook con cifras medidas y el interruptor de vuelta) y anota el gasto
   real en el ledger del proyecto si lo hay.

## Reglas

| # | Regla | Por qué |
|---|---|---|
| 1 | `push` solo en `main`; las ramas se prueban por `pull_request` | `push` a cualquier rama + `pull_request` prueba cada commit dos veces (43 % de los minutos en el precedente) |
| 2 | `concurrency` con `cancel-in-progress` en los PR, con el grupo por número de PR | Varios push seguidos: solo importa el último. En `main` no se cancela, para que cada merge conserve su resultado |
| 3 | Dos niveles: rápido en cada PR, completo (E2E, imagen Docker, demos de recuperación) en `main`, a mano o con una etiqueta (`ci-completo`) | El E2E y Docker suelen ser más de la mitad del tiempo y no hace falta repetirlos en cada push de una rama |
| 4 | Filtro de rutas para la documentación, **con lista de reincluidos** | Los cambios de docs no deben lanzar 25 min de CI, **pero** si un test lee un `.md` (runbooks, YAML de definición), su cambio sí debe lanzarlo. Un `paths-ignore: '**/*.md'` ciego deja pasar roturas |
| 5 | Un test que busque en el código las rutas de documentación que se leen y compruebe que el filtro las incluye | Así nadie puede romper la regla 4 en silencio al añadir un test nuevo |
| 6 | `timeout-minutes` en cada job (≈2× la duración normal) | El límite por defecto son 6 h: un cuelgue se come la cuota de un mes |
| 7 | Crons con la frecuencia que el negocio necesita, no más | Cada ejecución se redondea al minuto por job: un cron cada 5 min son ~8.600 min al mes |
| 8 | Cachés (`setup-node` con `cache`, etc.) y nada de `apt-get` innecesario | Instalar paquetes del sistema llega a costar 10–19 min en un mal día del espejo |
| 9 | Si el repo puede ser público, los runners estándar no consumen minutos | Es la palanca más barata, cuando procede |
| 10 | Las automatizaciones que dan servicio (crons de producto) no comparten cuota con un CI pesado | O el CI pesado va a un runner propio, o el producto va a otra cuenta o runner |

### Errores conocidos

- **Filtro de rutas:** los patrones se aplican en orden; uno con `!` excluye y uno positivo posterior
  vuelve a incluir. Si se usa `paths` con `!`, el primero debe ser positivo (`'**'`).
- **Anclas YAML** (`&rutas` / `*rutas`): no se puede contar con que el parser de Actions de esa cuenta
  las admita. Repite la lista y comprueba con el test que `push` y `pull_request` coinciden.
- **`labeled` en `pull_request.types`:** añadir cualquier etiqueta relanza el workflow. Pon
  `if: github.event.action != 'labeled' || github.event.label.name == '<etiqueta>'` y la
  `concurrency` **a nivel de job**, para que un evento descartado no cancele la ejecución en curso.
- **Los minutos de reloj no son los facturados:** los de reloj incluyen la cola, y la facturación
  redondea por job y multiplica macOS (×10) y Windows (×2). La cifra buena está en
  *Settings → Billing → Usage*.
- **Registrar un runner exige ser admin del repo**; una cuenta con solo push recibe 404 en la API
  de runners.

## Qué no hacer

- No subir el presupuesto como solución: compra tiempo, no arregla la causa.
- No desactivar tests para ahorrar minutos. Lo que se recorta es **cuándo** se ejecutan.
- No poner un runner propio en la máquina o el daemon Docker de producción: el CI ejecuta
  `docker compose down --volumes` y código de terceros.
- No afirmar ahorros sin decir que son una proyección; medir a final de mes.
