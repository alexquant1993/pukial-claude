---
name: handoff
description: Relevo entre sesiones de Claude Code. Guarda el estado del trabajo en .claude/HANDOFF.md (objetivo, qué quedó hecho, qué falta, decisiones tomadas y archivos tocados) para poder hacer /clear sin perder el hilo, y lo retoma en la sesión nueva. Úsala siempre que el usuario diga "handoff", "relevo", "guarda el estado", "guarda lo básico para continuar", "voy a limpiar el contexto", "antes del /clear", "dónde lo dejamos", "retomamos", "continúa donde quedamos" o cuando el contexto esté muy cargado y vaya a cambiar de tarea, aunque no nombre la skill.
---

# Handoff: relevo entre sesiones

El usuario limpia el contexto (`/clear`) a menudo para ahorrar tokens y pasar a otra parte del proyecto. Esta skill deja un archivo corto que una sesión nueva, sin memoria de la conversación, pueda leer y continuar como si nada hubiera pasado. Piensa en quien lo va a leer: otro agente que no vio nada y que solo tiene este archivo y el repositorio.

Hay dos modos:

- **Guardar** (por defecto, o con `/handoff`, `/handoff guardar`): escribe el relevo.
- **Retomar** (`/handoff retomar`, o "dónde lo dejamos", "retomamos"): lo lee y propone el siguiente paso.

Si no queda claro cuál quiere: en una sesión con trabajo hecho es guardar; en una sesión recién empezada es retomar.

## Modo guardar

### 1. Reúne los datos

Ejecuta en la raíz del proyecto (`git rev-parse --show-toplevel`; si no es un repositorio git, usa el directorio de trabajo):

```bash
git branch --show-current
git log --oneline -10
git status --short
git diff --stat HEAD
```

Combina eso con lo que pasó en la conversación. Git no ve todo: también cuentan los archivos fuera del repositorio (memoria de Claude, `~/.claude/...`, otros proyectos), los cambios en servicios externos (consolas web, cuentas, DNS) y las tareas que hizo el usuario a mano.

### 2. Escribe `.claude/HANDOFF.md`

Sobrescribe el archivo si existe: debe reflejar solo el estado actual, porque la historia ya está en git. Usa exactamente esta plantilla:

```markdown
# Handoff — <nombre del proyecto>

> Actualizado: <AAAA-MM-DD HH:MM> · Rama: `<rama>` · Último commit: `<hash corto> <mensaje>`

## 1. Objetivo

<Qué se intenta conseguir y por qué, en 1-3 frases. El objetivo general de la tarea, no solo lo último que se hizo.>

## 2. Qué quedó hecho

- <Hecho verificable, con referencia concreta: commit, archivo, URL, ID>

## 3. Qué falta

1. <Siguiente paso concreto, el primero es por donde se retoma>
2. <...>

- **Bloqueos / espera de terceros:** <lo que depende del usuario u otra persona, o "ninguno">

## 4. Decisiones tomadas

- **<Decisión>**: <por qué>. <Alternativa descartada, si la hubo.>

## 5. Archivos tocados

| Archivo         | Estado                                                   | Nota         |
| --------------- | -------------------------------------------------------- | ------------ |
| `ruta/relativa` | commit `abc123` / sin commit / sin push / fuera del repo | <qué cambió> |
```

Criterios para que el relevo sirva:

- **Concreto antes que bonito.** "Falta verificar el depósito de prueba en Perfil de pagos → Verificar" sirve; "Falta terminar la configuración" no.
- **Fechas absolutas.** "Mañana" no significa nada en otra sesión; escribe la fecha.
- **Las decisiones llevan el porqué.** Es lo que más se pierde al limpiar el contexto y lo que evita que la sesión nueva vuelva a discutir lo ya decidido o deshaga algo a propósito.
- **Restricciones vigentes en Decisiones.** Si el usuario pidió "no hacer push", "no tocar tal archivo" o "eso lo hago yo", anótalo: la sesión nueva no lo sabrá.
- **Estado real de cada archivo.** Distingue con commit, sin commit y sin push; marca los cambios que se dejan sin commit a propósito.
- **Corto.** Apunta a menos de 80 líneas. Si algo es largo (un plan, una especificación), enlaza el archivo en vez de copiarlo.
- **Nada de secretos.** Ni contraseñas, tokens, claves ni números de cuenta completos; usa referencias como `•••• 1234` o "en `.env`".

### 3. Mantenlo fuera de git

El usuario quiere el archivo fuera del control de versiones. Si es un repositorio git y `git check-ignore -q .claude/HANDOFF.md` falla, añade la línea `.claude/HANDOFF.md` a `.git/info/exclude` (local, no ensucia el `.gitignore` versionado ni los commits). Hazlo una sola vez.

### 4. Cierra

Muestra al usuario un resumen de 3-5 líneas (objetivo y primer paso pendiente), la ruta completa del archivo y dile que ya puede ejecutar `/clear` y empezar la sesión nueva con `/handoff retomar`.

Si durante la sesión aparecieron datos estables que valen para siempre (no para esta tarea), sugiere guardarlos también en la memoria del proyecto; el handoff es el estado de la tarea, la memoria son los hechos duraderos.

## Modo retomar

1. Lee `.claude/HANDOFF.md` en la raíz del proyecto. Si no existe, dilo y ofrece revisar `git log` y la memoria del proyecto para reconstruir el estado.
2. **Comprueba que sigue siendo verdad**, porque entre sesiones el usuario puede haber trabajado por su cuenta:
   - Compara la rama y el último commit del archivo con `git branch --show-current` y `git log --oneline -10`.
   - Revisa `git status --short` frente a la tabla de archivos.
   - Si algo no cuadra (commits nuevos, archivos que ya no están modificados, otra rama), señálalo en vez de asumir que el archivo manda.
3. Si el handoff tiene más de unos días, avísalo: los pasos pendientes pueden haber cambiado.
4. Presenta en pocas líneas: objetivo, dónde quedó y el primer paso pendiente, con las decisiones y restricciones que lo afectan.
5. Propón empezar por ese primer paso y espera confirmación antes de hacer cambios. El usuario puede querer cambiar de rumbo.

Al terminar la sesión retomada, el usuario volverá a pedir un handoff; entonces se sobrescribe con el nuevo estado.
