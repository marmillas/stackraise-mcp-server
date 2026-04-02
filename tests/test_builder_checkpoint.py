"""Tests for builder checkpoint workflow helpers."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

from abstract_backend_mcp.core import builder_checkpoint as checkpoint_module
from abstract_backend_mcp.core.builder_checkpoint import (
    CHECKPOINT_COMMIT_MESSAGE,
    CheckpointError,
    finalize_checkpoint,
    get_checkpoint_status,
    get_session_path,
    load_active_session,
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


def test_start_checkpoint_blocks_sensitive_paths_without_override(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    (repo / ".env").write_text("TOKEN=abc\n", encoding="utf-8")

    with pytest.raises(CheckpointError, match="Sensitive-looking files"):
        start_checkpoint(repo)


def test_start_checkpoint_allows_sensitive_paths_with_override(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    (repo / ".env").write_text("TOKEN=abc\n", encoding="utf-8")

    session = start_checkpoint(repo, allow_sensitive_autocommit=True)

    assert session.auto_commit_performed is True
    assert _run_git(repo, ["log", "-1", "--pretty=%s"]) == CHECKPOINT_COMMIT_MESSAGE


def test_start_checkpoint_rejects_duplicate_active_session(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    start_checkpoint(repo)

    with pytest.raises(CheckpointError, match="already exists"):
        start_checkpoint(repo)


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


def test_finalize_keep_clears_session_and_keeps_changes(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    start_checkpoint(repo)
    (repo / "sample.txt").write_text("builder-changes\n", encoding="utf-8")

    result = finalize_checkpoint(action="keep", repo_root=repo)

    assert result.action == "keep"
    assert (repo / "sample.txt").read_text(encoding="utf-8") == "builder-changes\n"
    assert not get_session_path(repo).exists()


def test_finalize_revert_requires_explicit_confirmation(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    start_checkpoint(repo)

    with pytest.raises(CheckpointError, match="confirm_revert='REVERTIR'"):
        finalize_checkpoint(action="revert", confirm_revert="", repo_root=repo)


def test_finalize_revert_blocks_cross_branch_without_override(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    start_checkpoint(repo)
    _run_git(repo, ["checkout", "-b", "other-branch"])

    with pytest.raises(CheckpointError, match="Revert blocked by default"):
        finalize_checkpoint(action="revert", confirm_revert="REVERTIR", repo_root=repo)

    assert get_session_path(repo).exists()


def test_finalize_revert_allows_cross_branch_with_override(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    session = start_checkpoint(repo)
    _run_git(repo, ["checkout", "-b", "other-branch"])
    (repo / "sample.txt").write_text("other-branch-change\n", encoding="utf-8")
    (repo / "tmp.txt").write_text("remove me\n", encoding="utf-8")

    result = finalize_checkpoint(
        action="revert",
        confirm_revert="REVERTIR",
        repo_root=repo,
        allow_cross_branch_revert=True,
    )

    assert result.action == "revert"
    assert result.reverted_to_sha == session.base_head_sha
    assert result.warnings
    assert (repo / "sample.txt").read_text(encoding="utf-8") == "base\n"
    assert not (repo / "tmp.txt").exists()
    assert not get_session_path(repo).exists()


def test_start_checkpoint_blocks_when_git_operation_in_progress(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    git_dir = get_session_path(repo).parent
    (git_dir / "MERGE_HEAD").write_text("dummy\n", encoding="utf-8")

    with pytest.raises(CheckpointError, match="Git operation is in progress"):
        start_checkpoint(repo)


def test_corrupted_session_file_reported_in_status_and_load(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    start_checkpoint(repo)
    get_session_path(repo).write_text("{bad-json", encoding="utf-8")

    status = get_checkpoint_status(repo)

    assert status.active_session is True
    assert status.session is None
    assert status.issues
    with pytest.raises(CheckpointError, match="corrupted"):
        load_active_session(repo)


def test_legacy_session_payload_with_extra_keys_is_supported(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    start_checkpoint(repo)
    session_path = get_session_path(repo)
    payload = json.loads(session_path.read_text(encoding="utf-8"))
    payload["checkpoint_enabled"] = True
    session_path.write_text(json.dumps(payload), encoding="utf-8")

    loaded = load_active_session(repo)

    assert loaded.session_id


def test_start_checkpoint_reports_timeout(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    original_run = checkpoint_module.subprocess.run

    def _fake_run(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        cmd = args[0]
        if isinstance(cmd, list) and cmd[:2] == ["git", "status"]:
            raise subprocess.TimeoutExpired(cmd=cmd, timeout=1)
        return original_run(*args, **kwargs)

    monkeypatch.setattr(checkpoint_module.subprocess, "run", _fake_run)

    with pytest.raises(CheckpointError, match="timed out"):
        start_checkpoint(repo, git_timeout_seconds=1)
