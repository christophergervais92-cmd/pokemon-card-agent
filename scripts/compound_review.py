#!/usr/bin/env python3
"""Compound review: daily context + rules → Anthropic → update RULE.md / .cursor/rules. Needs ANTHROPIC_API_KEY."""
import os
import sys

PROJECT_ROOT = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
DAILY_CONTEXT = os.path.join(PROJECT_ROOT, "logs", "daily-context.md")
RULE_MD = os.path.join(PROJECT_ROOT, "RULE.md")
RULES_DIR = os.path.join(PROJECT_ROOT, ".cursor", "rules")

def read_file(path: str) -> str:
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return ""

def read_rules_dir() -> str:
    if not os.path.isdir(RULES_DIR):
        return ""
    parts = []
    for name in sorted(os.listdir(RULES_DIR)):
        if name.endswith(".mdc") or name.endswith(".md"):
            p = os.path.join(RULES_DIR, name)
            if os.path.isfile(p):
                parts.append(f"## {name}\n{read_file(p)}")
    return "\n\n".join(parts) if parts else ""

def main() -> None:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ANTHROPIC_API_KEY not set. Skipping compound review.")
        return
    daily = read_file(DAILY_CONTEXT)
    current_rules = read_file(RULE_MD) or read_rules_dir()
    if not daily and not current_rules:
        print("No logs/daily-context.md or RULE.md/.cursor/rules found.")
        return
    try:
        import anthropic
    except ImportError:
        print("pip install anthropic for compound_review.py")
        return
    client = anthropic.Anthropic(api_key=api_key)
    prompt = f"""You are compounding learnings for this codebase. Below is (1) today's context and (2) current agent instructions. Extract key learnings; output a single updated instruction document that MERGES these learnings. Output only the new rule content, no preamble.

--- Daily context ---
{daily or "(none)"}

--- Current rules ---
{current_rules or "(none)"}

--- Updated rules ---
"""
    resp = client.messages.create(
        model=os.environ.get("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022"),
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )
    new_content = ""
    for block in resp.content:
        if hasattr(block, "text"):
            new_content += block.text
    if not new_content.strip():
        return
    if os.path.isfile(RULE_MD):
        with open(RULE_MD, "w", encoding="utf-8") as f:
            f.write(new_content.strip())
        print("Updated RULE.md")
    else:
        os.makedirs(RULES_DIR, exist_ok=True)
        out = os.path.join(RULES_DIR, "compound-learnings.mdc")
        with open(out, "w", encoding="utf-8") as f:
            f.write("---\ndescription: Compound learnings from daily review\nalwaysApply: true\n---\n\n")
            f.write(new_content.strip())
        print("Updated .cursor/rules/compound-learnings.mdc")

if __name__ == "__main__":
    main()
