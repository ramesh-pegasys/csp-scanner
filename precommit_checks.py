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

import subprocess
import re
import sys
from pathlib import Path
from datetime import datetime


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

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, cwd=Path(__file__).parent
        )
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
    success, output = run_command(
        ["black", "--check", "--diff", "app", "tests"], "black"
    )
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
        print("❌ MyPy type checking failed:")
        print(output)
    else:
        print("✅ MyPy type checking passed")
    return success


def run_pytest_coverage():
    """Run pytest with coverage and return the output."""
    print("Running pytest with coverage...")
    python_exe = get_python_executable()
    try:
        result = subprocess.run(
            [python_exe, "-m", "pytest", "--cov=app", "--cov-report=term-missing"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent,
        )
        return result.returncode == 0, result.stdout + result.stderr
    except subprocess.CalledProcessError as e:
        print(f"Error running pytest: {e}")
        return False, str(e)


def extract_coverage_percentage(output):
    """Extract the total coverage percentage from pytest output."""
    # Look for the TOTAL line
    lines = output.split("\n")
    for line in reversed(lines):
        if line.startswith("TOTAL"):
            # TOTAL                                     2583    240    91%
            parts = line.split()
            if len(parts) >= 4:
                try:
                    percentage = int(parts[-1].rstrip("%"))
                    return percentage
                except ValueError:
                    pass
    print("Could not find coverage percentage in pytest output")
    return None


def update_badge_in_file(file_path, percentage):
    """Update the coverage badge in the given file."""
    with open(file_path, "r") as f:
        content = f.read()

    # Pattern to match the coverage badge
    pattern = r"\[!\[Coverage\]\(https://img\.shields\.io/badge/coverage-[^%]*%25-brightgreen\)\]"

    # New badge
    new_badge = f"[![Coverage](https://img.shields.io/badge/coverage-{percentage}%25-brightgreen)](https://pytest-cov.readthedocs.io/)"

    if re.search(pattern, content):
        updated_content = re.sub(pattern, new_badge, content)
        with open(file_path, "w") as f:
            f.write(updated_content)
        print(f"Updated coverage badge in {file_path} to {percentage}%")
    else:
        print(f"Coverage badge not found in {file_path}")


def update_last_modified_date(file_path):
    """Update the last modified date in the given file."""
    with open(file_path, "r") as f:
        content = f.read()

    # Get the last commit date for the docs directory
    try:
        result = subprocess.run(
            [
                "git",
                "log",
                "-1",
                "--format=%cd",
                "--date=format:%B %d, %Y",
                "--",
                "docs/",
            ],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent,
        )
        if result.returncode == 0:
            current_date = result.stdout.strip()
        else:
            # Fallback to current date if git command fails
            current_date = datetime.now().strftime("%B %d, %Y")
    except Exception:
        # Fallback to current date if git is not available
        current_date = datetime.now().strftime("%B %d, %Y")

    # Pattern to match the last updated line
    pattern = r"\*\*Last Updated\*\*: .*"

    # New last updated line
    new_line = f"**Last Updated**: {current_date}"

    if re.search(pattern, content):
        updated_content = re.sub(pattern, new_line, content)
        with open(file_path, "w") as f:
            f.write(updated_content)
        print(f"Updated last modified date in {file_path} to {current_date}")
    else:
        # If no existing date, add it at the end
        if not content.endswith("\n"):
            content += "\n"
        content += f"\n---\n\n{new_line}"
        with open(file_path, "w") as f:
            f.write(content)
        print(f"Added last modified date to {file_path}: {current_date}")


def main():
    """Run all pre-commit checks."""
    print("🚀 Running pre-commit checks...\n")

    checks = []

    # Run quality checks
    checks.append(("Flake8", run_flake8()))
    checks.append(("Black", run_black()))
    checks.append(("MyPy", run_mypy()))

    # Run tests with coverage
    pytest_success, pytest_output = run_pytest_coverage()
    checks.append(("Pytest", pytest_success))

    if pytest_success:
        percentage = extract_coverage_percentage(pytest_output)
        if percentage is not None:
            print(f"Coverage: {percentage}%")

            # Update badges
            readme_path = Path(__file__).parent / "README.md"
            docs_index_path = Path(__file__).parent / "docs" / "index.md"

            update_badge_in_file(readme_path, percentage)
            update_badge_in_file(docs_index_path, percentage)

            # Update last modified date in docs
            update_last_modified_date(docs_index_path)
        else:
            print("❌ Could not extract coverage percentage")
    else:
        print("❌ Pytest failed:")
        print(pytest_output)

    # Summary
    print("\n📊 Summary:")
    all_passed = True
    for name, passed in checks:
        status = "✅" if passed else "❌"
        print(f"{status} {name}")
        if not passed:
            all_passed = False

    if all_passed:
        print("\n🎉 All checks passed!")
        sys.exit(0)
    else:
        print("\n💥 Some checks failed. Please fix the issues before committing.")
        sys.exit(1)


if __name__ == "__main__":
    main()
