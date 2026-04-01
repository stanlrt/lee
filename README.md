# NanoClaw Setup

## 1. Configure `.env`

Create `.env` in the project root:

```env
ASSISTANT_NAME=Nanolee
TELEGRAM_BOT_TOKEN=        # from @BotFather
FIRECRAWL_API_URL=http://172.17.0.1:3002
COGNEE_MCP_URL=http://172.17.0.1:8765/sse
ONECLI_URL=http://localhost:10254   # OneCLI credential gateway
TZ=Europe/Paris            # optional, for scheduler
```

## 2. Install dependencies and build

```bash
npm ci
npm run build
```

## 3. Build the agent container image

```bash
./container/build.sh
```

This takes a few minutes the first time. The image must exist before the service can handle messages.

## 4. Set up the systemd service

Create `/etc/systemd/system/nanoclaw.service`:

```ini
[Unit]
Description=NanoClaw
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=stan
Group=stan
WorkingDirectory=/home/stan/lee
ExecStart=/usr/bin/node dist/index.js
Restart=always
RestartSec=5
Environment=NODE_ENV=production

[Install]
WantedBy=multi-user.target
```

Then enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable nanoclaw
sudo systemctl start nanoclaw
```

Always use `systemctl` to manage the service — never `nohup` or manual node invocations alongside it.

If the service hangs on restart (stuck waiting for sudo password or never completing), a container is still running. Kill it first:

```bash
docker ps --filter "name=nanoclaw" -q | xargs -r docker kill
sudo systemctl restart nanoclaw --no-pager
```

## 5. Start background services

### LiteLLM proxy

Agent containers route all LLM calls through LiteLLM (Gemini Flash by default, Anthropic for heavy tasks).

Create `litellm/.env` (gitignored — must be recreated on each VPS):

```env
GEMINI_API_KEY=...
ANTHROPIC_API_KEY=...
```

Then start it:

```bash
cd litellm && docker compose up -d
```

Verify: `curl -s http://172.17.0.1:4000/health`

The bot will silently hang (typing indicator but no reply) if LiteLLM isn't running.

### Cognee MCP (memory)

Create an empty `cognee/.env` (gitignored — required even if empty):

```bash
touch cognee/.env
```

Install Python deps into the host venv (mounted into the container):

```bash
sudo apt install -y python3-venv python3-pip
python3 -m venv cognee/.venv
cognee/.venv/bin/pip install -r cognee/requirements.txt
```

Then build and start:

```bash
cd cognee && docker compose up -d --build
```

The first build takes a few minutes. Subsequent starts are fast.

## 6. Set up Firecrawl

See `firecrawl/README.md`.

## 6. Set up OneCLI (credential gateway)

Run `/init-onecli` in Claude Code to install OneCLI and migrate credentials from `.env` into the vault. Required for containers to access API keys.

## 7. Register groups/chats

Channels (Telegram, WhatsApp, etc.) must be registered in the database before the agent responds to them.

**Telegram:** Send `/chatid` to your bot to get the chat ID, then insert it:

```bash
node -e "
const db = require('better-sqlite3')('store/messages.db');
db.prepare(\`INSERT OR REPLACE INTO registered_groups
  (jid, name, folder, trigger_pattern, added_at, container_config, requires_trigger, is_main)
  VALUES ('tg:<chat_id>', '<name>', 'main', '@Nanolee', datetime('now'), NULL, 0, 0)\`).run();
"
```

Then restart: `sudo systemctl restart nanoclaw`

**WhatsApp / other channels:** Follow the relevant skill instructions (`/add-whatsapp`, `/add-telegram`, etc.).

## Verify

```bash
sudo systemctl status nanoclaw
journalctl -u nanoclaw -f
```

If the service shows active but the bot doesn't respond, check the logs — the container image may be missing or OneCLI may be unreachable.
