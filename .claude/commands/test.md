---
description: Run the full pytest suite with concise summary
allowed-tools: Bash(uv run pytest:*)
---

Run `uv run pytest tests/ -q` and report the result in one or two lines.

If anything fails:
- Show the failing test names and a short excerpt of the failure.
- Suggest using the `test-debugger` subagent for non-trivial failures.

Do not modify any code from this command — diagnosis only.
