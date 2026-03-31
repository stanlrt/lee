# NanoClaw

Personal Claude assistant. See [README.md](README.md) for philosophy and setup. See [docs/REQUIREMENTS.md](docs/REQUIREMENTS.md) for architecture decisions.

## Quick Context

Single Node.js process with skill-based channel system. Channels (WhatsApp, Telegram, Slack, Discord, Gmail) are skills that self-register at startup. Messages route to Claude Agent SDK running in containers (Linux VMs). Each group has isolated filesystem and memory.

## Key Files

| File                       | Purpose                                                             |
| -------------------------- | ------------------------------------------------------------------- |
| `src/index.ts`             | Orchestrator: state, message loop, agent invocation                 |
| `src/channels/registry.ts` | Channel registry (self-registration at startup)                     |
| `src/ipc.ts`               | IPC watcher and task processing                                     |
| `src/router.ts`            | Message formatting and outbound routing                             |
| `src/config.ts`            | Trigger pattern, paths, intervals                                   |
| `src/container-runner.ts`  | Spawns agent containers with mounts                                 |
| `src/task-scheduler.ts`    | Runs scheduled tasks                                                |
| `src/db.ts`                | SQLite operations                                                   |
| `groups/{name}/CLAUDE.md`  | Per-group memory (isolated)                                         |
| `container/skills/`        | Skills loaded inside agent containers (browser, status, formatting) |

## Secrets / Credentials / Proxy (OneCLI)

API keys, secret keys, OAuth tokens, and auth credentials are managed by the OneCLI gateway — which handles secret injection into containers at request time, so no keys or tokens are ever passed to containers directly. Run `onecli --help`.

## Cognee Memory Strategy

Use Cognee for durable, user-specific memory that should persist across sessions.

- **When to store:** user explicitly says "remember", or the fact is clearly long-lived and useful.
- **What to store:** preferences, stable profile facts, recurring constraints, project context, and decisions.
- **What not to store:** secrets, credentials, API keys, passwords, private keys, temporary task state, or one-off chatter.
- **Sensitive personal data:** ask for confirmation before storing unless the user explicitly requested storage.
- **Sensitive data handling:** store sensitive values in OneCLI only; in Cognee store only non-secret references (for example, vault key names or where to retrieve the secret).
- **Tool routing for secrets:** use OneCLI via the CLI/workflows (`onecli secrets ...`, `/init-onecli`) for create/read/update/delete of sensitive values; never send raw secret values to Cognee.
- **OneCLI command patterns:** use `onecli secrets list` to inspect secrets, `onecli secrets create --name <Name> --type <type> --value <value> --host-pattern <host>` to add a secret, and `/init-onecli` when setup/migration is needed.

Always follow the workflow:

1. `cognee_add` with clear, structured facts
2. `cognee_cognify` so data becomes queryable
3. `cognee_search` when recalling prior memory
4. If data is sensitive, use OneCLI tools instead of Cognee

## Skills

Four types of skills exist in NanoClaw. See [CONTRIBUTING.md](CONTRIBUTING.md) for the full taxonomy and guidelines.

- **Feature skills** — merge a `skill/*` branch to add capabilities (e.g. `/add-telegram`, `/add-slack`)
- **Utility skills** — ship code files alongside SKILL.md (e.g. `/claw`)
- **Operational skills** — instruction-only workflows, always on `main` (e.g. `/setup`, `/debug`)
- **Container skills** — loaded inside agent containers at runtime (`container/skills/`)

| Skill               | When to Use                                                       |
| ------------------- | ----------------------------------------------------------------- |
| `/setup`            | First-time installation, authentication, service configuration    |
| `/customize`        | Adding channels, integrations, changing behavior                  |
| `/debug`            | Container issues, logs, troubleshooting                           |
| `/update-nanoclaw`  | Bring upstream NanoClaw updates into a customized install         |
| `/init-onecli`      | Install OneCLI Agent Vault and migrate `.env` credentials to it   |
| `/qodo-pr-resolver` | Fetch and fix Qodo PR review issues interactively or in batch     |
| `/get-qodo-rules`   | Load org- and repo-level coding rules from Qodo before code tasks |

## Contributing

Before creating a PR, adding a skill, or preparing any contribution, you MUST read [CONTRIBUTING.md](CONTRIBUTING.md). It covers accepted change types, the four skill types and their guidelines, SKILL.md format rules, PR requirements, and the pre-submission checklist (searching for existing PRs/issues, testing, description format).

## Development

Run commands directly—don't tell the user to run them.

```bash
npm run dev          # Run with hot reload
npm run build        # Compile TypeScript
./container/build.sh # Rebuild agent container
```

Service management:
```bash
# macOS (launchd)
launchctl load ~/Library/LaunchAgents/com.nanoclaw.plist
launchctl unload ~/Library/LaunchAgents/com.nanoclaw.plist
launchctl kickstart -k gui/$(id -u)/com.nanoclaw  # restart

# Linux (systemd)
systemctl --user start nanoclaw
systemctl --user stop nanoclaw
systemctl --user restart nanoclaw
```

## Troubleshooting

**WhatsApp not connecting after upgrade:** WhatsApp is now a separate skill, not bundled in core. Run `/add-whatsapp` (or `npx tsx scripts/apply-skill.ts .claude/skills/add-whatsapp && npm run build`) to install it. Existing auth credentials and groups are preserved.

## Container Build Cache

The container buildkit caches the build context aggressively. `--no-cache` alone does NOT invalidate COPY steps — the builder's volume retains stale files. To force a truly clean rebuild, prune the builder then re-run `./container/build.sh`.
