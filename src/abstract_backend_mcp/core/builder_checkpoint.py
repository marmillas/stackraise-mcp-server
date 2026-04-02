"""Builder checkpoint workflow helpers.

This module implements a minimal checkpoint session for builder workflows:

1. Optionally auto-commit pending changes (message: ``checkpoint pre-build``).
2. Persist checkpoint metadata in ``.git``.
3. Finalize by keeping current changes or reverting hard to checkpoint SHA.
"""

from __future__ import annotations

import json
import subprocess
import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

CHECKPOINT_COMMIT_MESSAGE = "checkpoint pre-build"
REVERT_CONFIRMATION = "REVERTIR"
SESSION_FILENAME = "abstract_builder_checkpoint_session.json"


class CheckpointError(RuntimeError):
    """Raised when checkpoint workflow operations fail."""


@dataclass
class CheckpointSession:
    """Persistent metadata for an active builder checkpoint."""

    session_id: str
    created_at: str
    checkpoint_enabled: bool
    base_head_sha: str
    base_branch: str
    auto_commit_performed: bool


@dataclass
class FinalizeResult:
    """Result metadata after finalizing a checkpoint session."""

    action: str
    reverted_to_sha: str | None
    warnings: list[str]


def _run_git(repo_root: Path, args: list[str]) -> str:
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=repo_root,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise CheckpointError("git executable was not found in PATH") from exc
    except OSError as exc:
        raise CheckpointError(f"Unable to execute git command: {exc}") from exc
    if proc.returncode != 0:
        stderr = proc.stderr.strip() or "Unknown git error"
        cmd = " ".join(["git", *args])
        raise CheckpointError(f"{cmd} failed: {stderr}")
    return proc.stdout.strip()


def _resolve_repo_root(repo_root: Path | None = None) -> Path:
    start = (repo_root or Path.cwd()).resolve()
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=start,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise CheckpointError("git executable was not found in PATH") from exc
    except OSError as exc:
        raise CheckpointError(f"Unable to execute git command: {exc}") from exc
    if proc.returncode != 0:
        raise CheckpointError("Current directory is not inside a Git repository")
    return Path(proc.stdout.strip()).resolve()


def _resolve_git_dir(repo_root: Path) -> Path:
    raw_git_dir = _run_git(repo_root, ["rev-parse", "--git-dir"])
    git_dir = Path(raw_git_dir)
    if not git_dir.is_absolute():
        git_dir = (repo_root / git_dir).resolve()
    return git_dir


def _assert_no_git_operation_in_progress(git_dir: Path) -> None:
    markers = [
        "MERGE_HEAD",
        "REBASE_HEAD",
        "CHERRY_PICK_HEAD",
        "REVERT_HEAD",
        "rebase-apply",
        "rebase-merge",
    ]
    for marker in markers:
        if (git_dir / marker).exists():
            raise CheckpointError(
                f"Cannot start/finalize checkpoint while a Git operation is in progress ({marker})"
            )


def get_session_path(repo_root: Path | None = None) -> Path:
    """Return absolute path to the checkpoint session file in .git."""
    resolved_root = _resolve_repo_root(repo_root)
    git_dir = _resolve_git_dir(resolved_root)
    return git_dir / SESSION_FILENAME


def load_active_session(repo_root: Path | None = None) -> CheckpointSession:
    """Load active checkpoint session from .git.

    Raises:
        CheckpointError: if there is no active session or session is invalid.
    """
    session_path = get_session_path(repo_root)
    if not session_path.exists():
        raise CheckpointError("No active builder checkpoint session found")

    try:
        payload = json.loads(session_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CheckpointError("Checkpoint session file is corrupted") from exc

    try:
        return CheckpointSession(**payload)
    except TypeError as exc:
        raise CheckpointError("Checkpoint session file is invalid") from exc


def start_checkpoint(repo_root: Path | None = None) -> CheckpointSession:
    """Create a builder checkpoint.

    If the tree is dirty, creates an auto-commit first with message
    ``checkpoint pre-build``.
    """
    resolved_root = _resolve_repo_root(repo_root)
    git_dir = _resolve_git_dir(resolved_root)
    _assert_no_git_operation_in_progress(git_dir)

    session_path = git_dir / SESSION_FILENAME
    if session_path.exists():
        raise CheckpointError("An active builder checkpoint session already exists")

    status_output = _run_git(resolved_root, ["status", "--porcelain"])
    auto_commit_performed = False
    if status_output:
        _run_git(resolved_root, ["add", "-A"])
        _run_git(resolved_root, ["commit", "-m", CHECKPOINT_COMMIT_MESSAGE])
        auto_commit_performed = True

    session = CheckpointSession(
        session_id=str(uuid.uuid4()),
        created_at=datetime.now(UTC).isoformat(),
        checkpoint_enabled=True,
        base_head_sha=_run_git(resolved_root, ["rev-parse", "HEAD"]),
        base_branch=_run_git(resolved_root, ["rev-parse", "--abbrev-ref", "HEAD"]),
        auto_commit_performed=auto_commit_performed,
    )
    session_path.write_text(json.dumps(asdict(session), indent=2), encoding="utf-8")
    return session


def finalize_checkpoint(
    *,
    action: str,
    confirm_revert: str | None = None,
    repo_root: Path | None = None,
) -> FinalizeResult:
    """Finalize active checkpoint session by keeping or reverting changes."""
    normalized = action.strip().lower()
    if normalized not in {"keep", "revert"}:
        raise CheckpointError("Invalid action. Use 'keep' or 'revert'")

    resolved_root = _resolve_repo_root(repo_root)
    git_dir = _resolve_git_dir(resolved_root)
    _assert_no_git_operation_in_progress(git_dir)

    session_path = git_dir / SESSION_FILENAME
    session = load_active_session(resolved_root)
    warnings: list[str] = []

    current_branch = _run_git(resolved_root, ["rev-parse", "--abbrev-ref", "HEAD"])
    if current_branch != session.base_branch:
        warnings.append(
            "Current branch differs from checkpoint branch "
            f"('{current_branch}' != '{session.base_branch}')"
        )

    if normalized == "keep":
        session_path.unlink(missing_ok=True)
        return FinalizeResult(action="keep", reverted_to_sha=None, warnings=warnings)

    if (confirm_revert or "").strip() != REVERT_CONFIRMATION:
        raise CheckpointError(
            "Revert confirmation failed. Pass confirm_revert='REVERTIR' to continue"
        )

    _run_git(resolved_root, ["reset", "--hard", session.base_head_sha])
    _run_git(resolved_root, ["clean", "-fd"])
    session_path.unlink(missing_ok=True)

    return FinalizeResult(
        action="revert",
        reverted_to_sha=session.base_head_sha,
        warnings=warnings,
    )
