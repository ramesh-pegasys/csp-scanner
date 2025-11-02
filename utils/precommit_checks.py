#!/usr/bin/env python3
"""
Pre-commit check script that runs code quality tools and updates coverage badges.

This script performs the following checks:
- Runs flake8 for linting
- Runs black for code formatting (check mode)
- Runs mypy for type checking
- Runs pytest with coverage and updates badges in README.md and docs/index.md
- Updates the last modified date in docs/index.md
"""

import sys
import subprocess
import re
import json
from pathlib import Path
from datetime import datetime

project_root = Path(__file__).parent.parent.resolve()


def get_python_executable():
    """Get the appropriate Python executable, preferring venv."""
    venv_paths = [
        Path(__file__).parent / ".venv" / "bin" / "python",
        Path(__file__).parent / "venv" / "bin" / "python",
    ]

    for venv_python in venv_paths:
        if venv_python.exists():
            return str(venv_python)

    # Fall back to current Python
    return sys.executable


def run_command(cmd, description):
    """Run a command and return success status and output."""
    python_exe = get_python_executable()
    if cmd[0] == "python":
        cmd[0] = python_exe

    # Run in project root (parent of utils)
    print(f"[DEBUG] Running {description} in {project_root}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=project_root)
        success = result.returncode == 0
        output = result.stdout + result.stderr
        return success, output
    except Exception as e:
        print(f"Error running {description}: {e}")
        return False, str(e)


def run_flake8():
    """Run flake8 linting check."""
    print("Running flake8...")
    success, output = run_command(["flake8", "app", "tests"], "flake8")
    if not success:
        print("❌ Flake8 failed:")
        print(output)
    else:
        print("✅ Flake8 passed")
    return success


def run_black():
    """Run black formatting check."""
    print("Running black (check mode)...")
    success, output = run_command(["black", "--check", "."], "black")
    if not success:
        print("❌ Black formatting issues found:")
        print(output)
    else:
        print("✅ Black formatting check passed")
    return success


def run_mypy():
    """Run mypy type checking."""
    print("Running mypy...")
    success, output = run_command(["mypy", "app"], "mypy")
    if not success:
        print("❌ Mypy type errors:")
        print(output)
    else:
        print("✅ Mypy passed")
    return success


def run_pytest():
    """Run pytest with coverage."""
    print("Running pytest with coverage...")
    success, output = run_command(
        ["pytest", "--cov=app", "--cov-report=json", "tests"], "pytest"
    )
    if not success:
        print("❌ Pytest failed:")
        print(output)
    else:
        print("✅ Pytest passed")
    return success


def update_badges():
    """Update coverage badges in README.md and docs/index.md."""
    try:
        with open(project_root / "coverage.json", "r") as f:
            data = json.load(f)
        pct = data["totals"]["percent_covered"]
        badge = f"[![Coverage](https://img.shields.io/badge/coverage-{pct:.0f}%25-brightgreen)](https://pytest-cov.readthedocs.io/)"

        # Update README.md
        readme_path = project_root / "README.md"
        with open(readme_path, "r") as f:
            content = f.read()
        content = re.sub(r"\[!\[Coverage\]\([^)]+\)\]\([^)]+\)", badge, content)
        with open(readme_path, "w") as f:
            f.write(content)

        # Update docs/index.md
        index_path = project_root / "docs" / "index.md"
        with open(index_path, "r") as f:
            content = f.read()
        content = re.sub(r"\[!\[Coverage\]\([^)]+\)\]\([^)]+\)", badge, content)
        with open(index_path, "w") as f:
            f.write(content)

        print("✅ Coverage badges updated")
    except Exception as e:
        print(f"❌ Error updating badges: {e}")


def update_last_modified():
    """Update last modified date in docs/index.md."""
    try:
        now = datetime.now().strftime("%B %d, %Y")
        index_path = project_root / "docs" / "index.md"
        with open(index_path, "r") as f:
            content = f.read()
        content = re.sub(
            r"\*\*Last Updated\*\*: \w+ \d+, \d+", f"**Last Updated**: {now}", content
        )
        with open(index_path, "w") as f:
            f.write(content)
        print("✅ Last modified date updated")
    except Exception as e:
        print(f"❌ Error updating last modified date: {e}")


def main():
    print("\n--- Pre-commit Checks ---")
    all_passed = True
    if not run_flake8():
        all_passed = False
    if not run_black():
        all_passed = False
    if not run_mypy():
        all_passed = False
    if not run_pytest():
        all_passed = False
    if all_passed:
        update_badges()
        update_last_modified()
        print("\n✅ All pre-commit checks passed!")
    else:
        print("\n❌ Some pre-commit checks failed.")


if __name__ == "__main__":
    main()
