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

## 12) Gmail integration (start tool-only)

Inside Claude Code:

```text
/add-gmail
```

Choose `tool-only` first.

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

## 13) GitHub via MCP (chosen path)

1. Create a fine-grained PAT scoped only to required repos/permissions.
2. Configure GitHub MCP server in your Claude/NanoClaw MCP config.
3. Store token using OneCLI secret flow when available.

Test sequence:
1. Read-only MCP action (list repo metadata/issues)
2. Controlled write action in a sandbox repo (e.g., create draft issue)

## 14) Cognee installation

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

Run a smoke test based on current Cognee quickstart.

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
- GitHub MCP still authenticates
- Cognee retrieval test passes

## 16) Operations baseline

- Backup targets:
  - NanoClaw project state directories
  - `~/.gmail-mcp/`
  - Cognee data directories
- Keep monthly update cadence:
  - NanoClaw core + skills
  - OS package patches
  - token hygiene and rotation checks

## Current policy notes to keep in mind

- Gmail OAuth testing mode has user and consent constraints; for personal use this is usually fine.
- GitHub generally recommends fine-grained PATs over classic PATs where supported.
- Telegram group privacy defaults to restricted message visibility unless disabled.
