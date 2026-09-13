# Railway — AstraOS deploy notes

## Live services

- Web: https://web-production-20abf.up.railway.app
- API: https://api-production-c5e7.up.railway.app
- Project: `astraos` (Postgres + `api` + `web`)

## Service layout

| Service  | Root directory | Builder    | Notes                          |
|----------|----------------|------------|--------------------------------|
| Postgres | —              | image      | Railway Postgres plugin        |
| api      | `/apps/api`    | Dockerfile | Migrates + seeds on boot       |
| web      | `/apps/web`    | Dockerfile | Needs `NEXT_PUBLIC_API_URL`    |

Config as code: `apps/api/railway.toml`, `apps/web/railway.toml`.

## Required variables

API:

```text
DATABASE_URL=${{Postgres.DATABASE_URL}}
APP_ENV=production
ASTRAOS_DEMO_MODE=true
ASTRAOS_SEED=2026
FRONTEND_URL=https://${{web.RAILWAY_PUBLIC_DOMAIN}}
INTENT_PARSER_MODE=rule_based
RESPONSE_MODEL_MODE=COLD_START
SEMANTIC_EMBEDDING_PROVIDER=hashing
SEMANTIC_EMBEDDING_ALLOW_DOWNLOAD=false
PROTOCOL_ADAPTER=rest
```

Web (must be set before / during image build):

```text
NEXT_PUBLIC_API_URL=https://${{api.RAILWAY_PUBLIC_DOMAIN}}
```

## GitHub auto-deploy

Both `api` and `web` should be connected to `thnam02/AstraOS` on the deploy branch
(currently `nam/dev`). Pushes to that branch rebuild each service from its root directory
using the Dockerfile.

Reconnect / change branch:

```bash
railway service source connect --repo thnam02/AstraOS --branch nam/dev --service api
railway service source connect --repo thnam02/AstraOS --branch nam/dev --service web
```

Manual one-off deploy from local tree (no GitHub):

```bash
railway up -s api -d -y
railway up -s web -d -y
```

## Smoke checks

```bash
curl -sS https://api-production-c5e7.up.railway.app/health
curl -sS https://api-production-c5e7.up.railway.app/ready
curl -sSI https://web-production-20abf.up.railway.app/
```
