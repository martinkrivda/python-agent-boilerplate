#!/usr/bin/env python3
"""Bump the project version following SemVer and sync it across the repo.

Usage:
    uv run python scripts/release.py [patch|minor|major]

What it does:
1. Verifies the working tree is clean.
2. Reads the current version from `pyproject.toml` (single source of truth).
3. Computes the new version per SemVer rules.
4. Updates: pyproject.toml, deploy/helm/.../Chart.yaml (version + appVersion),
   deploy/k8s/deployment.yaml (app.kubernetes.io/version label).
5. Promotes `## [Unreleased]` in CHANGELOG.md to `## [X.Y.Z] — YYYY-MM-DD` and
   resets `## [Unreleased]` to an empty section.
6. Prints the next manual steps (commit + tag) — does NOT auto-commit, so you
   can review the changes first.
"""
from __future__ import annotations

import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# (path, regex pattern with one capture group, replacement template with `{}`)
FILES: list[tuple[Path, str, str]] = [
    (
        ROOT / "pyproject.toml",
        r'(?m)^version = "([\d.]+)"$',
        'version = "{}"',
    ),
    (
        ROOT / "deploy/helm/python-agent-boilerplate/Chart.yaml",
        r"(?m)^version: ([\d.]+)$",
        "version: {}",
    ),
    (
        ROOT / "deploy/helm/python-agent-boilerplate/Chart.yaml",
        r'(?m)^appVersion: "([\d.]+)"$',
        'appVersion: "{}"',
    ),
    (
        ROOT / "deploy/k8s/deployment.yaml",
        r'app\.kubernetes\.io/version: "([\d.]+)"',
        'app.kubernetes.io/version: "{}"',
    ),
]


def fail(msg: str) -> None:
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(1)


def current_version() -> str:
    text = (ROOT / "pyproject.toml").read_text()
    m = re.search(r'(?m)^version = "([\d.]+)"$', text)
    if not m:
        fail("could not find `version = \"...\"` in pyproject.toml")
    return m.group(1)


def bump(version: str, kind: str) -> str:
    parts = version.split(".")
    if len(parts) != 3 or not all(p.isdigit() for p in parts):
        fail(f"current version is not MAJOR.MINOR.PATCH: {version!r}")
    major, minor, patch = (int(p) for p in parts)
    if kind == "major":
        return f"{major + 1}.0.0"
    if kind == "minor":
        return f"{major}.{minor + 1}.0"
    if kind == "patch":
        return f"{major}.{minor}.{patch + 1}"
    fail(f"unknown bump kind: {kind!r} (expected patch|minor|major)")


def replace_in_files(new: str) -> None:
    for path, pattern, template in FILES:
        if not path.exists():
            print(f"  skip (missing): {path.relative_to(ROOT)}")
            continue
        text = path.read_text()
        new_text, n = re.subn(pattern, template.format(new), text, count=1)
        if n == 0:
            print(f"  warn:  no match in {path.relative_to(ROOT)}", file=sys.stderr)
            continue
        path.write_text(new_text)
        print(f"  bumped {path.relative_to(ROOT)}")


def promote_changelog(new: str) -> None:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    path = ROOT / "CHANGELOG.md"
    text = path.read_text()
    if "## [Unreleased]" not in text:
        fail("CHANGELOG.md is missing the `## [Unreleased]` header")
    text = text.replace(
        "## [Unreleased]",
        f"## [Unreleased]\n\n## [{new}] — {today}",
        1,
    )
    path.write_text(text)
    print(f"  promoted CHANGELOG entry to {new}")


def assert_clean_worktree() -> None:
    res = subprocess.run(
        ["git", "status", "--porcelain"],
        capture_output=True,
        text=True,
        cwd=ROOT,
        check=False,
    )
    if res.returncode != 0:
        fail("git status failed; is this a git repository?")
    if res.stdout.strip():
        fail("working tree has uncommitted changes — commit or stash them first")


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] not in ("patch", "minor", "major"):
        print(__doc__)
        sys.exit(2)

    assert_clean_worktree()

    cur = current_version()
    new = bump(cur, sys.argv[1])
    print(f"bumping {cur} → {new}\n")

    replace_in_files(new)
    promote_changelog(new)

    print(
        "\nDone. Review with `git diff`, then:\n"
        "  git add -u\n"
        f'  git commit -m "chore(release): v{new}"\n'
        f"  git tag -a v{new} -m 'v{new}'\n"
        "  git push && git push --tags"
    )


if __name__ == "__main__":
    main()
