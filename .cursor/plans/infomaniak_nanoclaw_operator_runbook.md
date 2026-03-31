# Infomaniak NanoClaw Operator Runbook

This is the execution-style version of your plan: linear steps, copy/paste commands, and verification checkpoints.

Assumptions:
- OS on server: Ubuntu 24.04
- Local machine: Windows 11 + PowerShell 7
- You already have an SSH key in Terminus
- Integration choices: GitHub via MCP, credentials via OneCLI Agent Vault

## 0) Variables to fill once

Use these values in all commands below.

```powershell
$ServerIp = "X.X.X.X"
$SshUser = "ubuntu"           # replace if Infomaniak image uses another default
$AdminUser = "stan"
$SshPort = "22"               # change if you set custom SSH port
$KeyPath = "C:\Users\YOU\.ssh\id_ed25519"
```

## 1) First login and lockout-safe session setup

From PowerShell:

```powershell
ssh -i "$KeyPath" "$SshUser@$ServerIp"
```

Immediately open a second terminal and keep both sessions active during hardening.

## 2) Base update and tools

On VPS:

```bash
sudo apt update && sudo apt -y upgrade
sudo apt -y install curl wget git unzip jq ca-certificates gnupg lsb-release fail2ban ufw rsync
```

## 3) Admin user and SSH key migration

On VPS:

```bash
id "${AdminUser}" || sudo adduser "${AdminUser}"
sudo usermod -aG sudo "${AdminUser}"
sudo rsync --archive --chown="${AdminUser}:${AdminUser}" ~/.ssh "/home/${AdminUser}"
```

Test admin login from PowerShell before continuing:

```powershell
ssh -i "$KeyPath" "$AdminUser@$ServerIp"
```

## 4) SSH hardening (safe order)

On VPS:

```bash
sudo cp /etc/ssh/sshd_config /etc/ssh/sshd_config.bak.$(date +%F-%H%M%S)
sudo nano /etc/ssh/sshd_config
```

Set at minimum:
- `PermitRootLogin no`
- `PasswordAuthentication no`
- `PubkeyAuthentication yes`
- Optional: `Port <custom_port>`

Validate and reload:

```bash
sudo sshd -t
sudo systemctl reload ssh
```

Verify you can still log in from a fresh terminal. Do not close existing root/default session until verified.

## 5) UFW and fail2ban

On VPS:

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ${SshPort}/tcp
# optional IP lock:
# sudo ufw allow from YOUR.PUBLIC.IP to any port ${SshPort} proto tcp
sudo ufw --force enable
sudo ufw status verbose
```

Enable fail2ban:

```bash
sudo systemctl enable --now fail2ban
sudo systemctl status fail2ban --no-pager
```

## 6) Automatic security updates

```bash
sudo apt -y install unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

## 7) Install Docker (Ubuntu 24)

```bash
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt -y install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker "${AdminUser}"
```

Re-login SSH as admin, then verify:

```bash
docker --version
docker compose version
docker run --rm hello-world
```

## 8) Install Node.js 20+

```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt -y install nodejs
node -v
npm -v
```

## 9) Clone NanoClaw and bootstrap

```bash
git clone https://github.com/<you>/nanoclaw.git
cd nanoclaw
git remote add upstream https://github.com/qwibitai/nanoclaw.git
```

Then launch:

```bash
claude
```

In Claude Code run:

```text
/setup
```

Choose:
- Linux + Docker
- OneCLI Agent Vault
- Channels you want now (Telegram and Gmail can be added now or later)

## 10) OneCLI secrets (no long-lived secrets in plain .env)

Use OneCLI workflow during setup. After configuration, verify secrets exist via OneCLI commands and confirm your `.env` does not contain long-lived provider tokens.

## 11) Telegram integration

Inside Claude Code:

```text
/add-telegram
```

Then:
1. Create bot with `@BotFather` (`/newbot`)
2. Set token in setup flow
3. In Telegram, send `/chatid` to your bot
4. Register returned `tg:<id>` as main chat

Optional for full group listening:
- BotFather -> Bot Settings -> Group Privacy -> Disable
- Remove and re-add bot to group

Validate:

```bash
systemctl --user status nanoclaw --no-pager
tail -f logs/nanoclaw.log
```

## 12) Gmail integration (full channel)

Inside Claude Code:

```text
/add-gmail
```

Choose `tool-only` first.
Choose `channel mode` (full channel).

OAuth setup:
1. Google Cloud Console -> create/select project
2. Enable Gmail API
3. Create OAuth Client ID (`Desktop app`)
4. Download JSON

On VPS:

```bash
mkdir -p ~/.gmail-mcp
cp /path/to/gcp-oauth.keys.json ~/.gmail-mcp/gcp-oauth.keys.json
npx -y @gongrzhe/server-gmail-autoauth-mcp auth
```

Complete browser consent flow, then restart:

```bash
systemctl --user restart nanoclaw
systemctl --user status nanoclaw --no-pager
```

Functional test from your main chat:
- Ask assistant to list labels
- Ask assistant to search recent emails

Additional full-channel validation:
- Send a new email to the connected inbox and confirm NanoClaw detects it.
- Confirm your desired trigger behavior for inbound Gmail events (avoid noisy auto-actions).

## 13) GitHub via MCP (chosen path)

1. Create a fine-grained PAT scoped only to required repos/permissions.
2. Configure GitHub MCP server in your Claude/NanoClaw MCP config.
3. Store token using OneCLI secret flow when available.

Test sequence:
1. Read-only MCP action (list repo metadata/issues)
2. Controlled write action in a sandbox repo (e.g., create draft issue)

## 14) Cognee installation and NanoClaw integration

On VPS:

```bash
sudo apt -y install python3 python3-venv python3-pip
curl -LsSf https://astral.sh/uv/install.sh | sh
source "$HOME/.local/bin/env"
mkdir -p ~/cognee && cd ~/cognee
uv venv
source .venv/bin/activate
uv pip install cognee
```

Create `.env` for Cognee with explicit providers (avoid accidental defaults):

```bash
cat > .env <<'EOF'
LLM_PROVIDER="openai"
LLM_MODEL="openai/gpt-4o-mini"
LLM_API_KEY="REPLACE_ME"
EMBEDDING_PROVIDER="openai"
EMBEDDING_MODEL="openai/text-embedding-3-small"
EMBEDDING_API_KEY="REPLACE_ME"
DB_PROVIDER="sqlite"
VECTOR_DB_PROVIDER="lancedb"
GRAPH_DATABASE_PROVIDER="kuzu"
EOF
```

Start Cognee service (Docker):

```bash
docker run -d \
  --name cognee \
  --restart unless-stopped \
  -p 8000:8000 \
  --env-file .env \
  -e ENABLE_BACKEND_ACCESS_CONTROL=false \
  cognee/cognee:latest
```

Quick health check:

```bash
docker ps --filter name=cognee
curl -sS http://127.0.0.1:8000/ | head
```

### 14.1) Important: OpenClaw plugin article vs NanoClaw

The Cognee article you shared describes an **OpenClaw plugin lifecycle** (`before_agent_start`, `agent_end`, plugin manifest, etc.).  
For **NanoClaw**, implement the same behavior directly in core flow (no OpenClaw plugin manifest needed):

- Pre-agent recall hook in `src/index.ts` before agent invocation.
- Post-agent sync hook in `src/index.ts` after successful run.
- Optional periodic maintenance in `src/task-scheduler.ts`.
- Keep HTTP client and mapping logic in a dedicated module (recommended: `src/memory/cognee.ts`).

### 14.2) NanoClaw memory flow to implement

1. **Startup sync**
   - Scan NanoClaw memory sources (group memory files / curated memory state).
   - Compute file hashes.
   - Push only new/changed memory payloads to Cognee dataset.
2. **Before each agent run**
   - Query Cognee with user prompt + minimal recent context.
   - Use graph-capable search mode (equivalent to `GRAPH_COMPLETION` from the article).
   - Inject only top relevant results into prompt context with strict token budget.
3. **After each successful agent run**
   - Re-scan memory files changed by the run.
   - Upsert changed items to Cognee.
4. **Scheduled maintenance**
   - Re-index stale entries.
   - Compact/merge low-value fragments.

### 14.3) Suggested config contract (NanoClaw-side)

Use env/config entries similar to:

```bash
COGNEE_BASE_URL="http://127.0.0.1:8000"
COGNEE_API_KEY="REPLACE_ME_IF_ENABLED"
COGNEE_DATASET_NAME="nanoclaw-main"
COGNEE_SEARCH_TYPE="GRAPH_COMPLETION"
COGNEE_AUTO_RECALL="true"
COGNEE_AUTO_INDEX="true"
COGNEE_MAX_RESULTS="8"
COGNEE_MAX_TOKENS="1200"
```

Notes:
- If API key auth is disabled locally, keep access bound to localhost/firewall.
- Separate dataset per scope (recommended): `group:<id>` or `workspace:<name>` to avoid cross-group bleed.

### 14.4) Validation checklist (NanoClaw-specific)

1. Trigger one conversation that should create memory.
2. Trigger a second conversation that should recall that memory.
3. Confirm recall quality in logs and response content.
4. Confirm unrelated group/topic data is not retrieved.

Useful checks:

```bash
docker logs --tail 200 cognee
systemctl --user status nanoclaw --no-pager
tail -f logs/nanoclaw.log
```

## 15) Reboot and recovery validation

```bash
sudo reboot
```

After reconnect:

```bash
systemctl --user status nanoclaw --no-pager
docker ps
```

Then verify end-to-end:

- Telegram prompt gets response
- Gmail tools still work
- 
- GitHub MCP still authenticates
- Cognee retrieval test passes (create -> recall -> isolation checks)

## 16) Operations baseline

- Backup targets:
  - NanoClaw project state directories
  - `~/.gmail-mcp/`
  - Cognee data directories / dataset exports
- Keep monthly update cadence:
  - NanoClaw core + skills
  - OS package patches
  - token hygiene and rotation checks

## 17) Smart model routing (LiteLLM + optional OpenRouter)

Decision:
- Use **LiteLLM** as the routing gateway (self-hosted on VPS).
- Use direct providers and optionally **OpenRouter** as an upstream source of additional models.
- Keep **Portkey out** for now.

Why this choice:
- Lowest lock-in and good cost control for long-term operation.
- Easy to add fallback, retry, and budget policies.
- Works with your goal of using cheap models for simple tasks and stronger models for complex reasoning.

### 17.1) Deploy LiteLLM on VPS

Example (quick start):

```bash
docker run -d \
  --name litellm \
  --restart unless-stopped \
  -p 4000:4000 \
  -e LITELLM_MASTER_KEY="REPLACE_ME" \
  -e OPENAI_API_KEY="REPLACE_ME_IF_USED" \
  -e ANTHROPIC_API_KEY="REPLACE_ME_IF_USED" \
  -e OPENROUTER_API_KEY="REPLACE_ME_IF_USED" \
  ghcr.io/berriai/litellm:main-latest \
  --port 4000
```

Health check:

```bash
docker ps --filter name=litellm
curl -sS http://127.0.0.1:4000/health
```

### 17.2) Routing policy (NanoClaw-side)

Implement three complexity tiers in NanoClaw:

- `simple`: short factual/chat/tool-routing tasks -> cheap fast model
- `standard`: normal coding/help tasks -> mid-cost model
- `complex`: architecture, deep debugging, high-risk edits -> strong reasoning model

Recommended escalation:
- Start at tier-selected model.
- Escalate one tier up on failure, low confidence, or tool/result ambiguity.

### 17.3) Integration points in NanoClaw

- Add/extend provider abstraction (recommended file: `src/model-router.ts`).
- Apply routing before agent invocation in `src/index.ts`.
- Keep Cognee retrieval and summarization on cheaper tiers where quality is acceptable.
- Reserve expensive models primarily for final synthesis on hard tasks.

### 17.4) Config contract (example)

```bash
MODEL_ROUTING_ENABLED="true"
MODEL_ROUTING_DEFAULT_TIER="standard"
LITELLM_BASE_URL="http://127.0.0.1:4000"
LITELLM_API_KEY="REPLACE_ME"

MODEL_SIMPLE="openrouter/<cheap-fast-model>"
MODEL_STANDARD="openrouter/<mid-model>"
MODEL_COMPLEX="anthropic/<thinking-model>"

MODEL_ESCALATION_ENABLED="true"
MODEL_MAX_ESCALATIONS="1"
MODEL_REQUEST_TOKEN_CAP="3500"
MODEL_DAILY_BUDGET_USD="REPLACE_ME"
```

### 17.5) Validation checklist

1. Send 5 trivial prompts and confirm simple tier is used.
2. Send 5 normal prompts and confirm standard tier is used.
3. Send 3 hard prompts and confirm complex tier (or escalation) is used.
4. Force one provider failure and verify fallback/escalation behavior.
5. Confirm daily budget and token caps are enforced.

Useful checks:

```bash
docker logs --tail 200 litellm
tail -f logs/nanoclaw.log
```

## Current policy notes to keep in mind

- Gmail OAuth testing mode has user and consent constraints; for personal use this is usually fine.
- GitHub generally recommends fine-grained PATs over classic PATs where supported.
- Telegram group privacy defaults to restricted message visibility unless disabled.
