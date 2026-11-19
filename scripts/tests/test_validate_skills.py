#!/usr/bin/env python3
"""Run with uv run --no-project --with pytest pytest scripts/tests."""

from contextlib import redirect_stderr, redirect_stdout
import importlib.util
import io
import os
from pathlib import Path
import subprocess

import pytest


SPEC = importlib.util.spec_from_file_location(
    "validate_skills", Path(__file__).resolve().parents[1] / "validate_skills.py"
)
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)
DESCRIPTION = "Use when testing the validator."


def git(root, *args):
    return subprocess.run(
        ["git", *args], cwd=root, check=True, capture_output=True, text=True
    )


def write(root, relative, text, executable=False):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    if executable:
        path.chmod(0o755)
    return path


@pytest.fixture
def repo(tmp_path, monkeypatch):
    for key in list(os.environ):
        if key.startswith("GIT_"):
            monkeypatch.delenv(key)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    git(tmp_path, "init", "--quiet")
    write(tmp_path, "README.md", "[Sample](skills/sample/)\n")
    write(tmp_path, "skills/sample/SKILL.md", f"---\nname: sample\ndescription: {DESCRIPTION}\n---\n")
    write(tmp_path, "scripts/check.py", "#!/usr/bin/env python3\npass\n", executable=True)
    git(tmp_path, "add", ".")
    return tmp_path


def validate(root):
    instance = validator.Validator(root)
    with redirect_stderr(io.StringIO()), redirect_stdout(io.StringIO()):
        result = instance.run()
    return result, "\n".join(instance.errors)


def assert_invalid(root, expected):
    result, errors = validate(root)
    assert result == 1
    assert expected in errors


def test_valid_staged_fixture_and_syntax_check_without_execution(repo):
    write(repo, "scripts/no execute.py", "raise RuntimeError('must not execute')\n", True)
    write(repo, "scripts/no execute.sh", "#!/bin/bash\nexit 99\n", True)
    git(repo, "add", ".")
    assert validate(repo) == (0, "")
    assert not list(repo.rglob("__pycache__"))


def test_unstaged_and_untracked_inputs_are_rejected(repo):
    write(repo, "README.md", "[Sample](skills/sample/)\nchanged\n")
    write(repo, "scripts/new.py", "pass\n", True)
    assert_invalid(repo, "working tree differs from the staged snapshot")
    assert_invalid(repo, "untracked validation inputs exist")


def test_category_skill_and_inventory_path(repo):
    category = repo / "skills/work"
    category.mkdir()
    (repo / "skills/sample").rename(category / "sample")
    git(repo, "add", ".")
    assert_invalid(repo, "README.md does not link skills/work/sample/")
    write(repo, "README.md", "[Sample](skills/work/sample/)\n")
    git(repo, "add", ".")
    assert validate(repo) == (0, "")
    git(repo, "add", ".")


def test_duplicate_names_across_categories_are_rejected(repo):
    write(repo, "skills/work/sample/SKILL.md",
          f"---\nname: sample\ndescription: {DESCRIPTION}\n---\n")
    write(repo, "README.md", "skills/sample/\nskills/work/sample/\n")
    git(repo, "add", ".")
    assert_invalid(repo, "duplicate skill name: sample")


@pytest.mark.parametrize("description, expected", [
    ("Use when x.", "25-64 characters"),
    ("Use when " + "x" * 60 + ".", "25-64 characters"),
    ("Missing the trigger sentence.", "must use"),
    ("Checks sample skills. Use when testing the validator.", "must use"),
    ("Use when testing the validator. Then report.", "must use"),
    ('"Use when testing the validator."', "unquoted"),
])
def test_description_length_and_shape(repo, description, expected):
    write(repo, "skills/sample/SKILL.md", f"---\nname: sample\ndescription: {description}\n---\n")
    git(repo, "add", ".")
    assert_invalid(repo, expected)


def test_description_allows_dots_inside_words(repo):
    description = "Use when editing a .md file."
    write(repo, "skills/sample/SKILL.md", f"---\nname: sample\ndescription: {description}\n---\n")
    git(repo, "add", ".")
    assert validate(repo) == (0, ""), "a dot inside a word is not a second sentence"


def test_name_and_inventory(repo):
    write(repo, "skills/sample/SKILL.md", f"---\nname: wrong\ndescription: {DESCRIPTION}\n---\n")
    write(repo, "README.md", "No inventory\n")
    git(repo, "add", ".")
    assert_invalid(repo, "declares name 'wrong'")
    assert_invalid(repo, "README.md does not link")


def test_executability_and_both_syntax_checks(repo):
    write(repo, "scripts/broken.py", "def broken(\n")
    write(repo, "scripts/broken.sh", "if then\n", True)
    git(repo, "add", ".")
    assert_invalid(repo, "script is not executable: scripts/broken.py")
    assert_invalid(repo, "python syntax failed")
    assert_invalid(repo, "shell syntax failed")


def test_staged_and_unstaged_whitespace(repo):
    write(repo, "README.md", "[Sample](skills/sample/)  \n")
    git(repo, "add", ".")
    assert_invalid(repo, "git diff --cached --check failed")
    write(repo, "README.md", "[Sample](skills/sample/)   \n")
    assert_invalid(repo, "git diff --check failed")


def test_missing_skill_file(repo):
    write(repo, "skills/old/note.txt", "no skill here\n")
    git(repo, "add", ".")
    assert_invalid(repo, "old is missing SKILL.md")


@pytest.mark.parametrize("text, expected", [
    ("name: sample\n", {}),
    ("---\nname: sample\n", {"name": "sample"}),
    ("---\nname:sample\nname: other\n---\n", {"name": "sample"}),
    ("---\ndescription:ignored\ndescription: first\ndescription: second\n---\n", {"description": "first"}),
    ("---\ndisable-model-invocation: perhaps\n---\n", {}),
    ("---\ndisable-model-invocation: true  \t\ndisable-model-invocation: false\n---\n", {"disable-model-invocation": "true"}),
    ("---\nname: sample\n---\ndisable-model-invocation: true\n", {"name": "sample"}),
])
def test_frontmatter_preserves_existing_extraction_rules(text, expected):
    assert validator.parse_frontmatter(text) == expected
