# Firecrawl Self-Hosted Setup (NanoClaw)

This folder runs a local Firecrawl API stack for NanoClaw.

It is intended to expose Firecrawl on the Docker bridge host IP so NanoClaw agent containers can reach it at:

- `http://172.17.0.1:3002`

---

## TL;DR (Known-Good Setup)

From `~/lee/firecrawl` on the VPS:

```bash
cp -n .env.example .env
docker compose down -v --remove-orphans
docker compose pull
docker compose up -d
```

If API crash-loops with `nuq.* relation does not exist`, run the recovery section below.

---

## Architecture

Compose services:

- `firecrawl-api` (`ghcr.io/firecrawl/firecrawl:latest`)
- `postgres` (`ghcr.io/firecrawl/nuq-postgres:latest`)
- `rabbitmq` (`rabbitmq:3-management-alpine`)
- `redis` (`redis:7-alpine`)

Network/port:

- Host bind: `172.17.0.1:3002:3002`

NanoClaw host `.env` should contain:

```bash
FIRECRAWL_API_URL=http://172.17.0.1:3002
```

---

## First-Time Bootstrap

1) Prepare env files:

```bash
cd ~/lee/firecrawl
cp -n .env.example .env
```

2) Start stack:

```bash
docker compose pull
docker compose up -d
```

3) Verify containers:

```bash
docker compose ps
docker compose logs --tail=120 firecrawl-api
```

4) Verify API responds (important: this stack binds to `172.17.0.1`, not localhost):

```bash
curl -sS -o /dev/null -w "http_code=%{http_code}\n" http://172.17.0.1:3002/
curl -sS http://172.17.0.1:3002/ | head -c 300
```

---

## Crash-Loop Recovery Playbook

### Symptom

`firecrawl-api` repeatedly restarts and logs contain errors like:

- `relation "nuq.queue_scrape" does not exist`
- `relation "nuq.queue_crawl_finished" does not exist`

### Root cause

NuQ schema/tables were not initialized in Postgres (or init SQL stopped early at pg_cron extension creation).

### Recovery (copy-paste)

Run from `~/lee/firecrawl`:

```bash
# 1) Ensure DB points to firecrawl database
sed -i '/^POSTGRES_USER=/d;/^POSTGRES_PASSWORD=/d;/^POSTGRES_DB=/d;/^NUQ_DATABASE_URL=/d' .env
cat >> .env <<'EOF'
POSTGRES_USER=firecrawl
POSTGRES_PASSWORD=firecrawl
POSTGRES_DB=firecrawl
NUQ_DATABASE_URL=postgresql://firecrawl:firecrawl@postgres:5432/firecrawl
EOF

# 2) Recreate stack clean
docker compose down -v --remove-orphans
docker compose pull
docker compose up -d
sleep 8

# 3) If API still crash-loops, manually apply NuQ SQL in firecrawl DB
docker compose exec postgres sh -lc '
psql -v ON_ERROR_STOP=1 -U firecrawl -d firecrawl -f /docker-entrypoint-initdb.d/010-nuq.sql
'

# 4) Verify nuq tables exist
docker compose exec postgres sh -lc '
psql -U firecrawl -d firecrawl -P pager=off -c "select schemaname, tablename from pg_tables where schemaname='\''nuq'\'' order by tablename;"
'

# 5) Recreate API and re-check
docker compose up -d --force-recreate firecrawl-api
sleep 10
docker compose ps
docker compose logs --tail=120 firecrawl-api
curl -sS -o /dev/null -w "http_code=%{http_code}\n" http://172.17.0.1:3002/
```

Expected table list includes:

- `nuq.queue_scrape`
- `nuq.queue_crawl_finished`
- `nuq.queue_scrape_backlog`
- `nuq.group_crawl`

---

## Operational Commands

From `~/lee/firecrawl`:

```bash
# start/stop/restart
docker compose up -d
docker compose stop
docker compose restart

# inspect
docker compose ps
docker compose logs --tail=200 firecrawl-api

# hard reset (destroys firecrawl DB data)
docker compose down -v --remove-orphans
```

---

## Notes / Gotchas

- `curl http://127.0.0.1:3002` can fail while service is healthy, because bind is on `172.17.0.1`.
- `AUTUMN_SECRET_KEY` and Supabase warnings are expected in basic self-host mode.
- If Firecrawl API image fails to pull for a specific tag, revert to `latest` or use a verified GHCR tag.
- Do not rely on temporary shell env exports for compose config; persist values in `firecrawl/.env`.

