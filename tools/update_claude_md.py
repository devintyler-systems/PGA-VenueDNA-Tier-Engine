#!/usr/bin/env python3
import os
import re
import subprocess
from datetime import datetime

SECTION_HEADER = "## Session Log"
PROJECT_HANDLE_PREFIX = "project_handle: "


def slugify(name: str) -> str:
    name = name.strip().lower()
    name = re.sub(r"[^a-z0-9]+", "_", name)
    name = re.sub(r"_+", "_", name).strip("_")
    return name or "project"


def infer_project_handle(cwd: str, content: str) -> str:
    first_h1 = None
    for line in content.splitlines():
        if line.startswith("# "):
            first_h1 = line[2:].strip()
            break
    base = first_h1 or os.path.basename(cwd)
    return slugify(base)


def get_git_summary(max_commits: int = 5) -> str:
    try:
        branch = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            stderr=subprocess.DEVNULL,
        ).decode("utf-8", "replace").strip()
    except Exception:
        branch = "unknown"

    try:
        log = subprocess.check_output(
            ["git", "log", f"-{max_commits}", "--pretty=format:%h | %ad | %s", "--date=short"],
            stderr=subprocess.DEVNULL,
        ).decode("utf-8", "replace")
    except Exception:
        return (
            f"- Branch: {branch}\n"
            "- Git not available or no commits; write a short note manually."
        )

    lines = log.strip().splitlines() if log.strip() else []
    if not lines:
        return (
            f"- Branch: {branch}\n"
            "- No recent commits; describe what you are about to work on."
        )

    out = [f"- Branch: {branch}", "- Recent changes (latest first):"]
    for line in lines:
        out.append(f"  - {line}")
    out.append("- Next focus: [fill this in before you start the session]")
    return "\n".join(out)


def ensure_project_handle(content: str, handle: str) -> str:
    lines = content.splitlines()
    for i, line in enumerate(lines[:8]):
        if line.startswith(PROJECT_HANDLE_PREFIX):
            lines[i] = f"{PROJECT_HANDLE_PREFIX}{handle}"
            return "\n".join(lines) + ("\n" if content.endswith("\n") else "")

    insert_at = 0
    if lines and lines[0].startswith("# "):
        insert_at = 1
    lines.insert(insert_at, f"{PROJECT_HANDLE_PREFIX}{handle}")
    return "\n".join(lines) + ("\n" if content.endswith("\n") else "")


def update_current_state(content: str) -> str:
    if SECTION_HEADER not in content:
        return content

    summary = get_git_summary()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    new_block = f"{SECTION_HEADER}\nSession stamp: {timestamp}\n\n{summary}\n"

    head, sep, tail = content.partition(SECTION_HEADER)
    if not sep:
        return content

    tail_lines = tail.splitlines()
    rest = tail_lines[1:]

    cut_idx = None
    for i, line in enumerate(rest):
        if line.startswith("## "):
            cut_idx = i
            break

    if cut_idx is None:
        return head + new_block

    remaining = "\n".join(rest[cut_idx:])
    return head + new_block + "\n" + remaining


def update_claude_md(path: str) -> None:
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    handle = infer_project_handle(os.getcwd(), content)
    content = ensure_project_handle(content, handle)
    content = update_current_state(content)

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Updated {path}")
    print(f"project_handle: {handle}")


if __name__ == "__main__":
    target = os.path.join(os.getcwd(), "CLAUDE.md")
    if not os.path.exists(target):
        print("No CLAUDE.md in this directory; run from the project root.")
    else:
        update_claude_md(target)
