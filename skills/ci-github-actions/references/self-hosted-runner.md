# A well-isolated self-hosted runner

Apply the rules in `SKILL.md` first; a self-hosted runner does not replace them.

## When yes and when no

| For | Against |
|---|---|
| Unlimited minutes on your own hardware | You maintain it: disk, patches, Docker images, browser caches |
| Persistent Docker cache: full runs get faster | If the machine is down, jobs queue (up to 24 h) and then fail |
| Moves heavy CI off the quota that product crons share | GitHub has announced per-minute charges for self-hosted runners before; check current pricing |
| | **Not for public repos:** a fork's pull request can run arbitrary code on the runner |

## Non-negotiable requirements

1. **Never on a production host or its Docker daemon.** CI creates and deletes Compose projects
   (`down --volumes`), runs `sudo apt-get` and hundreds of third-party packages. Use a dedicated,
   disposable VM.
2. **Network isolation enforced outside the VM.** Inside the VM the job has sudo and Docker (that is
   root), so a firewall inside the VM protects nothing. Use the hypervisor's or the network's
   firewall (for example, the per-VM firewall in Proxmox, security groups in a cloud):
   - Enable the firewall without changing existing behaviour first (accept-all defaults at cluster
     or host level), then add rules only for the runner VM.
   - Inbound: SSH only from one admin host. Outbound: the Internet and the DNS resolver;
     `DROP` to private ranges (`10/8`, `172.16/12`, `192.168.0.0/16`), CGNAT and overlay VPNs
     (`100.64/10`), link-local (`169.254/16`) and IPv6 ULA (`fc00::/7`).
   - Validate the rules before enabling them, and compare a baseline of your other services
     (production web, monitoring, hypervisor UI, SSH to other VMs) before and after.
   - Test isolation **from the VM and from a container inside it**: the LAN blocked; GitHub, the
     package registries, Docker Hub, browser download CDNs and the OS mirrors open.
3. **Out of the regular backup job:** it is disposable, and CI caches should not fill the backup
   store.
4. **Disk on separate storage from production** when there is a choice.

## Known pitfalls

- **SSH over an overlay VPN with asymmetric routing.** A VPN subnet router delivers the SYN from its
  VPN address, but the VM replies through its default gateway and the firewall drops the return
  traffic. Do not open the VPN range: jump through the admin host (`ssh -J admin@<host> runner@<vm>`)
  and allow port 22 only from that host's LAN address.
- **The SYN reaches the VM even though the rule looks right:** capture on the VM's network interface
  (`tcpdump -eni <iface>`) and look at the destination MAC of the reply. If it is the router's, it is
  the case above.
- **Registering the runner needs admin on the repo or org.** Prepare everything (the runner binary
  with its SHA-256 checked, dependencies, hooks) and leave only `config.sh` + `svc.sh install` for
  whoever holds the token.
- **`installdependencies.sh`** may report errors for some `libicu` versions; it is enough that one is
  installed.
- **Fixed ports in CI** (service containers, Compose projects): run a single runner, or allocate
  ports per job, so two jobs do not collide.

## Hygiene

- Pre-job hook (`ACTIONS_RUNNER_HOOK_JOB_STARTED` in `~/actions-runner/.env`): below ~15 GB free,
  clean up; below ~10 GB, fail with a message that points to the runbook.
- Post-job hook (`ACTIONS_RUNNER_HOOK_JOB_COMPLETED`): remove the CI Compose projects a cancelled job
  left behind.
- A daily Docker cleanup timer (images and build cache older than ~72 h, a cap on build cache) and
  Docker log rotation (`daemon.json`).
- Automatic security patches **without automatic reboot**.

## Fallback switch

`runs-on: ${{ vars.CI_RUNNER == 'github' && 'ubuntu-24.04' || '<label>' }}`: setting the repository
variable `CI_RUNNER=github` moves back to GitHub-hosted runners without a commit. Document that this
uses minutes.
