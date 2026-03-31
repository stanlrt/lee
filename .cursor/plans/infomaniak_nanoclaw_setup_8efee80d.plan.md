---
name: Infomaniak Nanoclaw Setup
overview: Build a current, Infomaniak-focused runbook to deploy NanoClaw + Cognee on Ubuntu 24 with Telegram, Gmail, and GitHub MCP integrations, using OneCLI Agent Vault for secrets.
todos:
  - id: collect-infomaniak-deltas
    content: Pull and include Infomaniak-specific first-login and SSH differences vs standard VPS flow.
    status: pending
  - id: write-deployment-runbook
    content: Draft full ordered runbook from provisioning through NanoClaw setup with OneCLI vault.
    status: pending
  - id: document-integrations
    content: Add Telegram, Gmail, and GitHub MCP integration steps with least-privilege credential guidance.
    status: pending
  - id: add-cognee-layer
    content: Add minimal Cognee install/config and progressive integration strategy.
    status: pending
  - id: add-validation-and-ops
    content: Append end-to-end test matrix, reboot checks, and security/maintenance procedures.
    status: pending
isProject: false
---

# Infomaniak VPS to NanoClaw + Cognee Granular Plan

## Scope

Produce a command-by-command runbook for Ubuntu 24 on Infomaniak that sets up:

- NanoClaw with OneCLI Agent Vault
- Telegram channel
- Gmail tools/channel
- GitHub MCP integration
- Cognee memory layer

## Provider Delta Checklist (Infomaniak First)

### Step 0.1 - Collect panel values

- Capture and verify from Infomaniak dashboard:
  - VPS public IPv4
  - default SSH username for your image
  - whether a cloud firewall/security group is active
  - whether password login is initially enabled

### Step 0.2 - First SSH from Windows PowerShell 7

- Use your Terminus key from PowerShell:
  - `ssh -i "C:\path\to\key" <user>@<server_ip>`
- Confirm host fingerprint and persist to known hosts.

### Step 0.3 - Lockout-safe baseline

- Open a second SSH session before changing SSH config.
- Keep one root/default session open until hardening is validated.

## Server Hardening Sequence (Ubuntu 24)

### Step 1.1 - Update and core packages

- `sudo apt update && sudo apt -y upgrade`
- `sudo apt -y install curl wget git unzip jq ca-certificates gnupg lsb-release fail2ban ufw`

### Step 1.2 - Create/admin user (if needed)

- `id <admin_user> || sudo adduser <admin_user>`
- `sudo usermod -aG sudo <admin_user>`
- `sudo rsync --archive --chown=<admin_user>:<admin_user> ~/.ssh /home/<admin_user>`

### Step 1.3 - SSH hardening with safe order

- Edit `/etc/ssh/sshd_config`:
  - `PermitRootLogin no`
  - `PasswordAuthentication no`
  - `PubkeyAuthentication yes`
  - optional custom `Port <port>`
- Validate config: `sudo sshd -t`
- Reload SSH: `sudo systemctl reload ssh`
- Verify login in second session before closing first.

### Step 1.4 - UFW and fail2ban

- Allow SSH first:
  - `sudo ufw allow <ssh_port>/tcp`
- Optional source restriction:
  - `sudo ufw allow from <your_public_ip> to any port <ssh_port> proto tcp`
- Enable firewall:
  - `sudo ufw default deny incoming`
  - `sudo ufw default allow outgoing`
  - `sudo ufw --force enable`
- Start fail2ban:
  - `sudo systemctl enable --now fail2ban`

### Step 1.5 - Auto-security updates

- `sudo apt -y install unattended-upgrades`
- `sudo dpkg-reconfigure -plow unattended-upgrades`

## Runtime Preparation for NanoClaw

### Step 2.1 - Install Node.js 20+

- Use NodeSource or nvm, then verify:
  - `node -v`
  - `npm -v`

### Step 2.2 - Install Docker on Ubuntu 24

- Install Docker Engine and plugins.
- Verify:
  - `docker --version`
  - `docker compose version`
  - `sudo docker run --rm hello-world`

### Step 2.3 - User permissions for Docker/systemd user service

- `sudo usermod -aG docker <admin_user>`
- Re-login SSH.
- Verify docker non-root use: `docker ps`

## NanoClaw Bootstrap (OneCLI Mode)

### Step 3.1 - Fork/clone and upstream remote

- `git clone https://github.com/<you>/nanoclaw.git`
- `cd nanoclaw`
- `git remote add upstream https://github.com/qwibitai/nanoclaw.git`

### Step 3.2 - Launch Claude Code and run setup

- `claude`
- Run `/setup`
- Select Linux + Docker + OneCLI Agent Vault flow.

### Step 3.3 - OneCLI secret strategy

- Register provider secrets via OneCLI commands.
- Ensure no long-lived API keys are left in `.env`.

### Step 3.4 - Service persistence checks

- Confirm user service status:
  - `systemctl --user status nanoclaw`
- Ensure linger enabled:
  - `loginctl show-user <admin_user> | rg Linger`
- Reboot validation planned later.

## Telegram Integration (Skill-Based)

### Step 4.1 - Apply integration

- In Claude Code: `/add-telegram`

### Step 4.2 - BotFather setup

- Create bot with `@BotFather` -> `/newbot`.
- Store token securely.

### Step 4.3 - Environment and sync

- Ensure `TELEGRAM_BOT_TOKEN` is configured via setup flow.
- Confirm env synced to runtime environment.

### Step 4.4 - Register chat(s)

- In Telegram with bot: `/chatid`
- Register returned `tg:<id>` as main channel.

### Step 4.5 - Optional group privacy change

- If full group listening needed:
  - BotFather -> Bot Settings -> Group Privacy -> disable.
- Re-add bot to group after privacy change.

### Step 4.6 - Validate

- Send test prompt in main chat.
- Check:
  - `systemctl --user status nanoclaw`
  - `tail -f logs/nanoclaw.log`

## Gmail Integration (Tool-Only First, Then Channel Optional)

### Step 5.1 - Apply integration

- In Claude Code: `/add-gmail`
- Choose **tool-only** first.

### Step 5.2 - Google Cloud OAuth

- Create/select GCP project.
- Enable Gmail API.
- Create OAuth client ID (Desktop app).
- Download JSON and place:
  - `~/.gmail-mcp/gcp-oauth.keys.json`

### Step 5.3 - Authorize locally

- `npx -y @gongrzhe/server-gmail-autoauth-mcp auth`
- Complete browser consent, produce `~/.gmail-mcp/credentials.json`.

### Step 5.4 - Rebuild/restart

- Clear stale runner directories if required.
- Rebuild container.
- Restart service:
  - `systemctl --user restart nanoclaw`

### Step 5.5 - Test tools

- Ask assistant to list labels/search emails.
- Confirm MCP tool calls succeed in logs.

### Step 5.6 - Optional channel mode

- Re-run `/add-gmail` and select channel mode when ready.
- Keep default unread primary filter initially.

### Step 5.7 - Policy caveats

- Document OAuth testing mode limits and sensitive scope verification path if you ever expose beyond personal use.

## GitHub MCP Integration (Selected Path)

### Step 6.1 - Token model

- Create a fine-grained PAT (preferred) scoped to required repos and minimal permissions.
- Fall back to classic PAT only for unsupported endpoints.

### Step 6.2 - MCP registration

- Add GitHub MCP server to Claude/NanoClaw MCP config.
- Store token through OneCLI-managed secrets when possible.

### Step 6.3 - Validation

- Run read-only checks first (list repo metadata/issues).
- Then run one controlled write test (e.g., draft issue in sandbox repo).

## Cognee Installation and Minimal Wiring

### Step 7.1 - Python environment

- Install Python version compatible with current Cognee docs.
- `uv venv && source .venv/bin/activate`
- `uv pip install cognee`

### Step 7.2 - Minimal env config

- Create `.env` with explicit provider variables:
  - `LLM_`*
  - `EMBEDDING_`*
  - DB provider settings
- Start with local defaults (SQLite + LanceDB + Kuzu) to avoid extra infra.

### Step 7.3 - Smoke test

- Run simple ingest + retrieval example.
- Validate persistence directories and permissions.

### Step 7.4 - Integration strategy

- Introduce Cognee in one flow first (e.g., persistent memory for project notes), then expand.

## Ops, Backups, and Recovery

### Step 8.1 - Backups

- Back up:
  - NanoClaw state directories
  - `~/.gmail-mcp/`
  - Cognee data directories
- Define retention and restore test cadence.

### Step 8.2 - Logging and monitoring

- Add log rotation for service and app logs.
- Define daily health checks and alert conditions.

### Step 8.3 - Secret incident playbook

- Revoke and rotate Telegram/Gmail/GitHub credentials.
- Reauthorize Gmail MCP and revalidate MCP connections.

### Step 8.4 - Update cadence

- NanoClaw core updates via upstream merge.
- Skill updates via `/update-skills` or `/update-nanoclaw`.
- Monthly dependency/security patch pass.

## End-to-End Acceptance Checklist

### Step 9.1 - Functional

- Telegram message -> assistant response
- Gmail label/search -> successful response
- GitHub MCP read -> success
- Cognee retrieve previously ingested memory -> success

### Step 9.2 - Resilience

- `sudo reboot`
- Verify nanoclaw auto-recovers:
  - `systemctl --user status nanoclaw`
- Verify Telegram/Gmail/GitHub flows still work after reboot.

## Documentation Sources to Cite in Final Runbook

- NanoClaw docs:
  - Quickstart
  - Integrations: Telegram, Gmail
  - Skills system
  - Configuration
- Cognee installation/configuration docs
- Telegram Bot API and BotFather behavior
- GitHub authentication docs (fine-grained PAT guidance)
- Infomaniak SSH first-connection documentation

