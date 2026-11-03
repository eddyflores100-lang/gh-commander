# gh-commander — cosecha autónoma de ofertas (Lever + Ashby)

Brazo de adquisición del agente **gh_commander** (AliceLabs LLC, fundador Edison Flores).
Este repo corre una **GitHub Action diaria** que cosecha ofertas de trabajo de las **APIs públicas** de Lever y Ashby, las filtra por categoría, las puntúa y publica la cola deduplicada lista para el motor de postulaciones.

## Qué hace exactamente

1. Consulta las APIs públicas (sin auth) de Lever (`api.lever.co/v0/postings/{org}`) y Ashby (`api.ashbyhq.com/posting-api/job-board/{org}`) para ~28 organizaciones vigiadas.
2. Filtra por categorías: `design` · `web` · `ai` · `crm` (excluye roles de ingeniería/seniority fuera de perfil).
3. Puntúa cada oferta: +40 remoto, +30 ubicación remota/anywhere, +50 Ecuador/LatAm, −10 USA cost.
4. Deduplica por `key` (org/id) y por `(org, título)` — persistente vía commit del estado en el repo.
5. Publica `scripts/gh/data/multi_queue.json` (schema: `ats`, `key`, `company`, `title`, `category`, `location`, `score`, `apply_url`, `harvested`).

## Garantías

- **Sin secrets**: solo APIs públicas verificadas en vivo (3-nov-2026). Ninguna credencial vive en este repo.
- **NO envía postulaciones**: este repo solo cosecha y prepara la cola. La ejecución de formularios la hace el motor gh_commander v4 (con validador post-acción) en el Chrome del propietario mediante la extensión Agent Bridge.
- **Caducidad consciente**: las orgs muertas (404) se saltan solas y se cachean; añadir orgs nuevas = editar `LEVER_ORGS` / `ASHBY_ORGS` en `scripts/gh/harvest_multi.py` (slug del job board de jobs.lever.co / jobs.ashbyhq.com).

## Corrida

- Programada: **13:00 UTC diario = 08:00 Ecuador** (`America/Guayaquil`, UTC-5, sin horario de verano).
- Manual: pestaña **Actions → cosecha-tableros → Run workflow**.
- Nota de GitHub: las Actions programadas se pausan automáticamente tras 60 días de inactividad del repo; reactivarlas desde la pestaña Actions o lanzar una corrida manual.
- La cola completa también es consumible vía raw: `https://raw.githubusercontent.com/eddyflores100-lang/gh-commander/main/scripts/gh/data/multi_queue.json`.

## Uso local (sin GitHub)

```bash
python3 scripts/gh/harvest_multi.py                 # cosechar todo
python3 scripts/gh/harvest_multi.py --cats design,ai
python3 scripts/gh/harvest_multi.py --orgs linear   # solo una org
python3 scripts/gh/harvest_multi.py --fresh         # reconstruir cola ignorando vistas
```

Requisitos: Python 3.8+ y `curl` en PATH. Sin dependencias pip.

## Contexto del funnel (3-nov-2026)

253 ofertas procesables · 1 enviada · 2 en submit-check (recheck listo) · 231 pendientes.
Estado y KPI por categoría los mantiene `gh_report.py` en el entorno del agente.

## Licencia

MIT — Copyright (c) 2026 Edison Flores (AliceLabs LLC)
