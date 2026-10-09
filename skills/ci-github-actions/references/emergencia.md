# Emergencia: minutos o presupuesto de Actions agotados

Síntoma: los workflows fallan o no arrancan en **todos** los repos privados de la cuenta, a menudo
sin log (el job no llega a empezar), y los crons «dejan de funcionar» a la vez.

## 1. Confirmar

```bash
gh run list -R OWNER/REPO --limit 5 --json workflowName,event,conclusion,createdAt
```

Varios repos con `failure` desde la misma hora, sin cambios de código, apuntan a la cuota. La
confirmación está en *Settings → Billing → Usage* (la API de facturación pide el scope `user`).

## 2. Reactivar primero lo que da servicio

Lista los workflows programados de cada repo de la cuenta (`gh api repos/OWNER/REPO/actions/workflows`)
e identifica los que sostienen un producto (publicación, notificaciones, SEO, copias).

1. **Desactiva el workflow pesado** para que no se coma el margen nuevo:
   `gh workflow disable <nombre> -R OWNER/REPO`.
2. **Sube el presupuesto lo justo** en *Settings → Billing → Budgets*. Es gasto: lo decide el
   owner, no el agente. Calcúlalo con el consumo diario de los workflows de producto hasta el fin de
   ciclo, y anótalo en el ledger de gasto del proyecto.
3. **Relanza a mano** los crons críticos (`gh workflow run <nombre> -R OWNER/REPO`) y comprueba
   que terminan en `success`.

## 3. Arreglar la causa

Vuelve al flujo de `SKILL.md`: diagnóstico, reglas y test. Reactiva el workflow pesado
(`gh workflow enable`) solo cuando ya cumpla las reglas o corra en un runner propio.
