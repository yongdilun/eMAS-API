# Factory-Agent Chat Rollout Guide

## Mode Selection

Set `VITE_CHAT_MODE`:
- `legacy`: existing `/ai/chats` mode only.
- `factory_agent`: new factory-agent mode for all users.
- `rollout`: percentage rollout by user id hash.

When `VITE_CHAT_MODE=rollout`, set:
- `VITE_FACTORY_AGENT_ROLLOUT_PERCENT=0..100`
- `VITE_FACTORY_AGENT_USER_ID=<stable-user-id>`

Optional local override (browser):
- `localStorage.setItem('chat_mode_override', 'legacy')`
- `localStorage.setItem('chat_mode_override', 'factory_agent')`
- `localStorage.removeItem('chat_mode_override')`

## Required Endpoint Config

- `VITE_FACTORY_AGENT_BASE_URL=http://127.0.0.1:8000`
- Optional auth token:
  - `VITE_FACTORY_AGENT_BEARER_TOKEN=<token>`

## Internal Validation

Run smoke flow:

```bash
npm run factory-agent-smoke
```

Optional env for smoke:
- `FACTORY_AGENT_BASE_URL`
- `FACTORY_AGENT_BEARER_TOKEN`
- `FACTORY_AGENT_USER_ID`
- `FACTORY_AGENT_INTENT`
- `FACTORY_AGENT_APPROVAL_DECISION=approve|reject`

## Recommended Phase Progression

1. `legacy` in production (baseline).
2. `rollout` at 5% for internal operators.
3. `rollout` at 25%.
4. `rollout` at 50%.
5. `factory_agent` at 100% once stable.

