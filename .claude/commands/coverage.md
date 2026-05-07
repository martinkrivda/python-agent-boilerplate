---
description: Run pytest with line + branch coverage report
allowed-tools: Bash(uv:*)
---

Run the test suite with coverage:

1. If `pytest-cov` is not installed yet (check `pyproject.toml`'s dev group), install it first:
   ```bash
   uv add --group dev pytest-cov
   ```

2. Run with coverage:
   ```bash
   uv run pytest tests/ --cov=app --cov-branch --cov-report=term-missing
   ```

3. Report:
   - Overall percentage.
   - Modules below 80%.
   - The first few "missing" line ranges per under-covered module.

Don't propose new tests from this command — surface the gaps so the user can prioritise.
