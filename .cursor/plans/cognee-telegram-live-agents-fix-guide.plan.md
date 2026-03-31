---
name: ""
overview: ""
todos: []
isProject: false
---

# Cognee Tools Missing in Telegram Live Agents - Fix Guide

This guide fixes the issue where Telegram live agents do not see Cognee tools.

## Root Cause

The runtime `query()` call in `container/agent-runner/src/index.ts` sets `mcpServers` programmatically (`nanoclaw`, `gmail`, `github`) but does not include `cognee`.

Because `mcpServers` is explicitly set in code, the Cognee server entry written to per-group settings is not applied to this runtime path. Result: `mcp__cognee__*` is allowed but no Cognee server is registered.

## Step-by-Step Fix

1. Open `container/agent-runner/src/index.ts`.
2. Find the `query({ options: { ... mcpServers: { ... } } })` block in `runQuery()`.
3. Add a `cognee` MCP server entry inside `mcpServers`.
4. Keep `allowedTools` entry `mcp__cognee__*` (already present).
5. Prefer `host.docker.internal` for cross-platform host reachability; keep current bridge IP as fallback if desired.

## Recommended Code Change

Inside `mcpServers`, add:

```ts
cognee: {
  type: "sse",
  url: process.env.COGNEE_MCP_URL || "http://host.docker.internal:8765/sse",
},
```

Notes:

- This keeps behavior configurable using `COGNEE_MCP_URL`.
- If your runtime cannot resolve `host.docker.internal`, set:
  - `COGNEE_MCP_URL=http://172.17.0.1:8765/sse`

## Optional Host-Side Config Consistency

For consistency with runtime defaults, you can also align the generated per-group settings in `src/container-runner.ts` to use the same URL strategy. This is optional for the immediate fix but reduces future drift.

## Verification Checklist

1. Start or restart the Cognee MCP service:
  - `docker compose -f cognee/docker-compose.yaml up -d`
2. Restart NanoClaw so new agent-runner config is active.
3. In Telegram, send a prompt that forces tool discovery/use, for example:
  - "List available Cognee tools and then run a small Cognee query."
4. Confirm logs show Cognee MCP registration and/or tool calls.
5. Confirm agent response references successful `mcp__cognee__*` tool execution.

## Troubleshooting

- If tools still do not appear:
  - Verify Cognee server is reachable from containers:
    - `curl http://host.docker.internal:8765/sse`
  - If unreachable, set `COGNEE_MCP_URL` to `http://172.17.0.1:8765/sse` and restart.
- If tools appear but fail at runtime:
  - Check Cognee container logs:
    - `docker logs cognee-mcp --tail 200`
  - Verify required Cognee environment variables and keys are present.

## Rollback

If needed, remove the `cognee` entry from `mcpServers` in `container/agent-runner/src/index.ts` and restart NanoClaw.