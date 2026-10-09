# Runner propio (self-hosted) bien aislado

Caso de referencia: VM 220 `gh-runner` en el R620 de Pukial (Proxmox), montada el 2026-10-09 para
el CI de pukial-flow. Runbook completo y archivos (cloud-init, reglas de firewall, hooks):
`pukial-flow/docs/operations/ci-runner-r620.md` y `docs/operations/ci-runner-r620/`.

## Cuándo sí y cuándo no

| A favor | En contra |
|---|---|
| Minutos ilimitados (hoy sin coste en GitHub) | Hay que mantenerlo: disco, parches, imágenes de Docker, cachés de Playwright |
| Caché de Docker persistente: las ejecuciones completas van más rápido | Si la máquina cae, los jobs se quedan en cola (hasta 24 h) |
| Saca el CI pesado de la cuota compartida con los crons de producto | GitHub anunció que cobraría por minuto de runner propio y lo aplazó: vigilarlo |

Primero se aplican las reglas de `SKILL.md`; el runner propio no sustituye a eso.

## Requisitos no negociables

1. **Nunca en el host ni en el daemon Docker de producción.** El CI levanta y borra proyectos
   Compose (`down --volumes`), ejecuta `sudo apt-get` y cientos de dependencias de npm. Usa una
   VM dedicada y desechable.
2. **Aislamiento de red fuera de la VM.** Dentro de la VM el job tiene sudo y Docker (es root),
   así que nftables en la propia VM no protege. En Proxmox:
   - `cluster.fw`: `enable: 1` con `policy_in/out: ACCEPT`, para que nada existente cambie.
   - `host.fw`: `enable: 0`, para que el host no se filtre.
   - `<vmid>.fw` con `firewall=1` en la NIC: entrada solo SSH desde el host; salida a Internet y
     DNS del router; `DROP` a `10/8`, `172.16/12`, `192.168.0.0/16`, `100.64/10` (Tailscale),
     `169.254/16` y `fc00::/7`.
   - Compila (`pve-firewall compile`) **antes** de activar, y compara una línea base de servicios
     (web de producción, monitorización, interfaz de Proxmox, SSH de las VMs) antes y después.
   - Prueba el aislamiento **desde la VM y desde un contenedor**: la LAN bloqueada; GitHub, npm,
     Docker Hub, la CDN de Playwright y apt abiertos.
3. **Fuera del backup diario** (`pvesh set /cluster/backup/<job> --exclude ...`): es desechable y
   el almacén de backups no debe llenarse con cachés de CI.
4. **Disco en un almacenamiento distinto del de producción** si lo hay (`local-lvm` frente a
   `data-projects`).

## Errores conocidos

- **SSH por Tailscale con enrutamiento asimétrico.** El subnet router entrega el SYN con su IP
  Tailscale (`100.x`), pero la VM responde por su gateway (el router) y el firewall descarta la
  vuelta. No abras `100.64/10`: entra saltando por el host (`ssh -J root@<host> runner@<vm>`) y
  permite el 22 solo desde la IP LAN del host.
- **El SYN llega a la VM aunque la regla parezca bien:** mira en `tcpdump -eni tap<vmid>i0` la MAC
  de destino de la respuesta. Si es la del router, es el caso anterior.
- **Registrar el runner exige admin del repo.** Prepara todo (binario con SHA-256 comprobado,
  dependencias, hooks) y deja solo `config.sh` + `svc.sh install` para quien tenga el token.
- **`installdependencies.sh`** muestra errores de `libicu7x`: prueba versiones; basta con que haya
  una instalada (Ubuntu 24.04 trae la 74).
- **Puertos fijos en el CI** (servicios en 55432, Compose en 55433…): un solo runner, o puertos por
  job, para que dos jobs no choquen.

## Higiene

- Hook antes del job (`ACTIONS_RUNNER_HOOK_JOB_STARTED` en `~/actions-runner/.env`): con menos de
  15 GB libres limpia; con menos de 10 GB falla con un mensaje que apunta al runbook.
- Hook después del job: retira los proyectos Compose del CI que deje un job cancelado.
- Timer diario de limpieza de Docker (imágenes y caché de build de más de 72 h, tope de 20 GB de
  caché de build) y log de Docker con rotación (`daemon.json`).
- Parches de seguridad automáticos **sin reinicio automático**.

## Interruptor de vuelta

`runs-on: ${{ vars.CI_RUNNER == 'github' && 'ubuntu-24.04' || '<etiqueta>' }}`: con la variable
de repositorio `CI_RUNNER=github` se vuelve a los runners de GitHub sin commit. Documenta que eso
consume minutos.
