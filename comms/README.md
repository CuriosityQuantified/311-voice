# Agent Communication Protocol

Two agents share this folder: **Claude** and **Hermes**. This folder is how they
coordinate so they don't clobber each other's edits.

## Files

| File | Purpose |
|---|---|
| `comms/log.md` | Append-only message log. Both agents post here. Newest at the bottom. |
| `../.claude-progress.md` | Live project state: what's done, in progress, blocked, and who owns what. |

## Rules

1. **Before editing any file, read `comms/log.md` and `../.claude-progress.md`.**
   Check whether the other agent is mid-edit on that file or owns it.
2. **Append, never overwrite, in `comms/log.md`.** Add a new dated, signed entry at
   the bottom. Do not edit or delete the other agent's entries.
3. **Claim a file before working on it.** Post a `CLAIM:` entry naming the file(s),
   then update `.claude-progress.md` ownership. Release with a `DONE:` entry.
4. **Hand off explicitly.** When you finish something the other agent needs, post a
   `HANDOFF:` entry stating what changed and what they should do next.
5. **Ask, don't assume.** If you need a decision the other agent or the user owns,
   post a `QUESTION:` entry and stop touching the contested area.
6. **Never commit secrets.** `API.md` and `.env` are gitignored. Don't add the live
   key to any tracked file or to `comms/`.

## Entry format (in log.md)

```
### YYYY-MM-DD HH:MM — <AGENT> — <TYPE>
<message>
```

Where `<TYPE>` is one of: CLAIM, DONE, HANDOFF, QUESTION, NOTE.
