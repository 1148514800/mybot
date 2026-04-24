# Errors Log

Store unresolved or candidate failures discovered while working on this MyBot project.

Use this file for:

- tool failures worth remembering
- browser/session failures
- execution-flow bugs
- repeated mistakes in storage, memory, state, or session handling

Promote stable fixes into:

- `workspace/instructions/TOOLS.md`
- `workspace/instructions/SOUL.md`
- `workspace/instructions/AGENTS.md`

Template:

```markdown
## [ERR-YYYYMMDD-XXX] short_name

**Logged**: ISO-8601 timestamp
**Priority**: low | medium | high | critical
**Status**: pending
**Area**: agent | tools | browser | memory | session | state | config | docs

### Summary
One-line description of the failure

### Error
Actual error output or failure symptom

### Context
- What was being attempted
- Which file / tool / workflow was involved

### Suggested Fix
What should change next time

### Promotion Target
- TOOLS.md | SOUL.md | AGENTS.md | memory.json | none yet

---
```
