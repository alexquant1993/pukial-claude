#!/usr/bin/env python3
"""Diagnóstico del consumo de GitHub Actions de un repositorio.

Run: python3 -I diagnostico-ci.py OWNER/REPO [--runs 200] [--desde AAAA-MM-DD] [--detalle 5]

Necesita `gh` autenticado con lectura del repositorio. Solo lee: no cambia nada.

Muestra, para las últimas ejecuciones:
  - cuántas hay por workflow, evento, rama y resultado;
  - cuántas repiten un commit ya probado (push + pull_request del mismo SHA);
  - la duración de reloj (mediana y p90) y los minutos aproximados;
  - en las N más recientes, los pasos más lentos de cada job.

Los minutos son de reloj (creación → última actualización): incluyen la espera en cola y no
aplican el redondeo por job ni los multiplicadores de macOS/Windows. Sirven para comparar y
encontrar la causa; la cifra facturada está en Settings → Billing → Usage.
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
        sys.exit(f"gh {' '.join(args)} falló:\n{out.stderr.strip()}")
    return json.loads(out.stdout or "null")


def ts(value: str | None) -> dt.datetime | None:
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00")) if value else None


def minutos(inicio: str | None, fin: str | None) -> float:
    a, b = ts(inicio), ts(fin)
    return (b - a).total_seconds() / 60 if a and b and b > a else 0.0


def percentil(valores: list[float], p: float) -> float:
    if not valores:
        return 0.0
    orden = sorted(valores)
    return orden[min(len(orden) - 1, int(len(orden) * p))]


def tabla(titulo: str, contador: collections.Counter, top: int = 8) -> None:
    print(f"\n{titulo}")
    for clave, n in contador.most_common(top):
        print(f"  {n:5d}  {clave}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("repo", help="OWNER/REPO")
    parser.add_argument("--runs", type=int, default=200, help="ejecuciones a leer (máx. 1000)")
    parser.add_argument("--desde", help="solo ejecuciones creadas desde esta fecha (AAAA-MM-DD)")
    parser.add_argument("--detalle", type=int, default=5, help="ejecuciones recientes con desglose de pasos")
    args = parser.parse_args()

    campos = "databaseId,workflowName,event,headBranch,headSha,conclusion,createdAt,updatedAt"
    runs = gh("run", "list", "-R", args.repo, "--limit", str(args.runs), "--json", campos) or []
    if args.desde:
        runs = [r for r in runs if r["createdAt"] >= args.desde]
    if not runs:
        sys.exit("Sin ejecuciones en el rango pedido.")

    info = gh("repo", "view", args.repo, "--json", "visibility") or {}
    print(f"Repositorio {args.repo} ({info.get('visibility', '?')}): {len(runs)} ejecuciones, "
          f"{runs[-1]['createdAt'][:10]} → {runs[0]['createdAt'][:10]}")
    if info.get("visibility") == "PUBLIC":
        print("  Repositorio público: los runners estándar de GitHub no consumen minutos.")

    duraciones = [minutos(r["createdAt"], r["updatedAt"]) for r in runs]
    por_workflow: dict[str, float] = collections.defaultdict(float)
    for r, m in zip(runs, duraciones):
        por_workflow[r["workflowName"]] += m
    print(f"\nMinutos de reloj: total ~{sum(duraciones):.0f}; mediana {percentil(duraciones, 0.5):.1f}, "
          f"p90 {percentil(duraciones, 0.9):.1f} por ejecución")
    for nombre, m in sorted(por_workflow.items(), key=lambda kv: -kv[1]):
        print(f"  ~{m:6.0f} min  {nombre}")

    tabla("Por evento", collections.Counter(r["event"] for r in runs))
    tabla("Por rama", collections.Counter(r["headBranch"] for r in runs))
    tabla("Por resultado", collections.Counter(r["conclusion"] or "en curso" for r in runs))

    # Un mismo commit probado más de una vez por el mismo workflow (push + pull_request,
    # reintentos o push repetidos).
    grupos: dict[tuple[str, str], list[int]] = collections.defaultdict(list)
    for i, r in enumerate(runs):
        grupos[(r["workflowName"], r["headSha"])].append(i)
    extra = [i for idx in grupos.values() if len(idx) > 1 for i in idx[1:]]
    minutos_extra = sum(duraciones[i] for i in extra)
    print(f"\nCommits probados más de una vez: {sum(1 for v in grupos.values() if len(v) > 1)}; "
          f"ejecuciones sobrantes {len(extra)} (~{minutos_extra:.0f} min, "
          f"{100 * minutos_extra / max(sum(duraciones), 1):.0f} %)")

    eventos = collections.Counter(r["event"] for r in runs)
    if eventos["push"] and eventos["pull_request"]:
        ramas_push = {r["headBranch"] for r in runs if r["event"] == "push"}
        if len(ramas_push - {"main", "master"}) > 0:
            print("  Aviso: hay push en ramas que no son main y también pull_request: "
                  "cada commit con PR abierto se prueba dos veces.")

    if args.detalle:
        print(f"\nPasos más lentos en las {args.detalle} ejecuciones más recientes terminadas:")
        hechas = [r for r in runs if r["conclusion"]][: args.detalle]
        for r in hechas:
            datos = gh("run", "view", str(r["databaseId"]), "-R", args.repo, "--json", "jobs") or {}
            for job in datos.get("jobs", []):
                pasos = sorted(
                    ((minutos(p.get("startedAt"), p.get("completedAt")), p["name"]) for p in job.get("steps", [])),
                    reverse=True,
                )[:4]
                total = minutos(job.get("startedAt"), job.get("completedAt"))
                print(f"  {r['createdAt'][:16]} {r['event']:<12} {job['name'][:30]:<30} {total:5.1f} min · "
                      + "; ".join(f"{n[:28]} {m:.1f}" for m, n in pasos))

    print("\nSiguiente paso: comparar con las reglas de la skill (SKILL.md, «Reglas»).")


if __name__ == "__main__":
    main()
