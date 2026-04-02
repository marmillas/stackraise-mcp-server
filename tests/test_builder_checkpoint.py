"""Tests for builder checkpoint workflow helpers."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from abstract_backend_mcp.core.builder_checkpoint import (
    CHECKPOINT_COMMIT_MESSAGE,
    CheckpointError,
    finalize_checkpoint,
    get_session_path,
    start_checkpoint,
)


def _run_git(repo: Path, args: list[str]) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    return proc.stdout.strip()


def _init_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()

    _run_git(repo, ["init"])
    _run_git(repo, ["config", "user.name", "Test User"])
    _run_git(repo, ["config", "user.email", "test@example.com"])

    (repo / "sample.txt").write_text("base\n", encoding="utf-8")
    _run_git(repo, ["add", "sample.txt"])
    _run_git(repo, ["commit", "-m", "initial"])
    return repo


def test_start_checkpoint_clean_tree_creates_session_without_autocommit(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)

    before_sha = _run_git(repo, ["rev-parse", "HEAD"])
    session = start_checkpoint(repo)

    assert session.base_head_sha == before_sha
    assert session.auto_commit_performed is False
    assert get_session_path(repo).exists()


def test_start_checkpoint_dirty_tree_creates_autocommit(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    (repo / "sample.txt").write_text("dirty\n", encoding="utf-8")

    session = start_checkpoint(repo)

    assert session.auto_commit_performed is True
    assert _run_git(repo, ["log", "-1", "--pretty=%s"]) == CHECKPOINT_COMMIT_MESSAGE


def test_finalize_revert_restores_checkpoint_state(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    session = start_checkpoint(repo)

    (repo / "sample.txt").write_text("changed by builder\n", encoding="utf-8")
    (repo / "temp.txt").write_text("untracked\n", encoding="utf-8")

    result = finalize_checkpoint(action="revert", confirm_revert="REVERTIR", repo_root=repo)

    assert result.action == "revert"
    assert result.reverted_to_sha == session.base_head_sha
    assert (repo / "sample.txt").read_text(encoding="utf-8") == "base\n"
    assert not (repo / "temp.txt").exists()
    assert not get_session_path(repo).exists()


def test_finalize_revert_requires_explicit_confirmation(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    start_checkpoint(repo)

    with pytest.raises(CheckpointError, match="confirm_revert='REVERTIR'"):
        finalize_checkpoint(action="revert", confirm_revert="", repo_root=repo)
