# CT-AI

Private autonomous AI workspace for long-running coding, research, and monitoring jobs.

## Current milestone: Foundation v0.1

Implemented:
- provider abstraction and sequential fallback
- persistent job state
- checkpoint persistence
- quota-aware `waiting_for_quota` state with scheduled retry timestamp
- minimal CLI entry point
- fallback unit test
- third-party attribution policy

## Architecture

```text
User / UI
   |
Task Manager
   |
Persistent Job Runner ---- Checkpoints
   |
Provider Router
   |---- Provider A
   |---- Provider B
   '---- OmniRoute-compatible providers (next milestone)
```

## Local development

Requires Node.js 22+.

```bash
npm install
npm run typecheck
npm test
npm run dev -- "your goal"
```

With no providers configured, a submitted job is intentionally persisted as `waiting_for_quota` rather than being lost.

## Next milestone

1. Add an OmniRoute-compatible OpenAI provider adapter.
2. Add provider health/quota cooldown tracking.
3. Add a scheduler that resumes due jobs after process/server restarts.
4. Expand checkpoints from one-shot completion into multi-step agent execution.
5. Add Git workspace/tool execution behind explicit safety boundaries.

See `THIRD_PARTY_NOTICES.md` before adapting upstream source.
