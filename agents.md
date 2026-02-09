# Agents.md — Living knowledge base

This file describes what the **compound review** (nightly loop) does. In Cursor, the actual instructions the AI reads are **RULE.md** and **.cursor/rules/**; those are the files the loop updates. Think of this doc as the “AGENTS.md” concept: a living knowledge base that grows every night.

---

## What the compound review does

The agent will:

1. **Find all your threads from the last 24 hours**  
   *(In Cursor: use **logs/daily-context.md** — paste a short summary of the day’s work, or leave empty to only refine existing rules.)*

2. **Check if each thread ended with a "compound" step** (extracting learnings)  
   *(When using AGENT_CMD, the agent can do this. When using the Python fallback, we merge **logs/daily-context.md** with current rules.)*

3. **For threads that didn’t, retroactively extract the learnings**  
   *(The review step extracts patterns, gotchas, and context from daily context + current rules.)*

4. **Update the relevant instruction files with patterns, gotchas, and context**  
   *(In Cursor we update **RULE.md** or **.cursor/rules/compound-learnings.mdc**.)*

5. **Commit and push to main**  
   *(The script commits changes to RULE.md / .cursor/rules and pushes to main.)*

Your **RULE.md** and **.cursor/rules/** become a **living knowledge base that grows every night**.

---

## In this project

- **scripts/daily-compound-review.sh** — runs at 10:30 PM (launchd).
- **logs/daily-context.md** — optional daily summary for compound review.
- **agents.md** — this file; human-readable description of the process (not auto-updated by the script).
