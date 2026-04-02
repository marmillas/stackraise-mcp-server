"""Builder checkpoint workflow helpers.

This module provides a robust checkpoint workflow for builder sessions:

1. Optionally auto-commit pending changes (message: ``checkpoint pre-build``).
2. Persist checkpoint metadata in ``.git`` atomically.
3. Finalize by keeping current changes or reverting hard to checkpoint SHA.
"""

from __future__ import annotations

import json
import os
import subprocess
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

CHECKPOINT_COMMIT_MESSAGE = "checkpoint pre-build"
REVERT_CONFIRMATION = "REVERTIR"
SESSION_FILENAME = "abstract_builder_checkpoint_session.json"
LOCK_FILENAME = "abstract_builder_checkpoint_session.lock"

DEFAULT_GIT_TIMEOUT_SECONDS = 30
DEFAULT_LOCK_STALE_SECONDS = 900

SENSITIVE_SUFFIXES = (".pem", ".key", ".p12", ".pfx", ".crt", ".cer")
SENSITIVE_EXACT_NAMES = (
    ".env",
    ".env.local",
    ".env.development",
    ".env.production",
    "id_rsa",
    "id_ed25519",
    "credentials.json",
)
SENSITIVE_KEYWORDS = (
    "secret",
    "token",
    "credential",
    "password",
    "passwd",
    "private_key",
)

SESSION_REQUIRED_FIELDS = (
    "session_id",
    "created_at",
    "base_head_sha",
    "base_branch",
    "auto_commit_performed",
)


class CheckpointError(RuntimeError):
    """Raised when checkpoint workflow operations fail."""


@dataclass
class CheckpointSession:
    """Persistent metadata for an active builder checkpoint."""

    session_id: str
    created_at: str
    base_head_sha: str
    base_branch: str
    auto_commit_performed: bool


@dataclass
class FinalizeResult:
    """Result metadata after finalizing a checkpoint session."""

    action: str
    reverted_to_sha: str | None
    warnings: list[str]


@dataclass
class CheckpointStatus:
    """Repository checkpoint status snapshot."""

    active_session: bool
    session: CheckpointSession | None
    session_path: str
    lock_present: bool
    lock_stale: bool
    issues: list[str]


def _run_git(repo_root: Path, args: list[str], *, timeout_seconds: int) -> str:
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except FileNotFoundError as exc:
        raise CheckpointError("git executable was not found in PATH") from exc
    except subprocess.TimeoutExpired as exc:
        cmd = " ".join(["git", *args])
        raise CheckpointError(f"{cmd} timed out after {timeout_seconds}s") from exc
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
            timeout=DEFAULT_GIT_TIMEOUT_SECONDS,
        )
    except FileNotFoundError as exc:
        raise CheckpointError("git executable was not found in PATH") from exc
    except subprocess.TimeoutExpired as exc:
        raise CheckpointError(
            "git rev-parse --show-toplevel timed out while resolving repository root"
        ) from exc
    except OSError as exc:
        raise CheckpointError(f"Unable to execute git command: {exc}") from exc

    if proc.returncode != 0:
        raise CheckpointError("Current directory is not inside a Git repository")
    return Path(proc.stdout.strip()).resolve()


def _resolve_git_dir(repo_root: Path) -> Path:
    raw_git_dir = _run_git(
        repo_root,
        ["rev-parse", "--git-dir"],
        timeout_seconds=DEFAULT_GIT_TIMEOUT_SECONDS,
    )
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


def _parse_status_paths(status_output: str) -> list[str]:
    paths: list[str] = []
    for raw_line in status_output.splitlines():
        if not raw_line:
            continue
        candidate = raw_line[3:] if len(raw_line) > 3 else raw_line
        if " -> " in candidate:
            candidate = candidate.split(" -> ", 1)[1]
        candidate = candidate.strip()
        if candidate:
            paths.append(candidate)
    return paths


def _find_sensitive_paths(paths: list[str]) -> list[str]:
    matched: list[str] = []
    for raw_path in paths:
        normalized = raw_path.replace("\\", "/").lower()
        name = Path(normalized).name
        if name in SENSITIVE_EXACT_NAMES:
            matched.append(raw_path)
            continue
        if name.endswith(SENSITIVE_SUFFIXES):
            matched.append(raw_path)
            continue
        if any(keyword in normalized for keyword in SENSITIVE_KEYWORDS):
            matched.append(raw_path)
    return matched


def _write_session_atomic(session_path: Path, payload: dict[str, Any]) -> None:
    tmp_path = session_path.with_name(f"{session_path.name}.tmp")
    tmp_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    tmp_path.replace(session_path)


def _session_from_payload(payload: dict[str, Any]) -> CheckpointSession:
    missing = [field for field in SESSION_REQUIRED_FIELDS if field not in payload]
    if missing:
        missing_txt = ", ".join(missing)
        raise CheckpointError(f"Checkpoint session file is invalid (missing: {missing_txt})")

    return CheckpointSession(
        session_id=str(payload["session_id"]),
        created_at=str(payload["created_at"]),
        base_head_sha=str(payload["base_head_sha"]),
        base_branch=str(payload["base_branch"]),
        auto_commit_performed=bool(payload["auto_commit_performed"]),
    )


def _is_stale_lock(lock_path: Path, stale_after_seconds: int = DEFAULT_LOCK_STALE_SECONDS) -> bool:
    if not lock_path.exists():
        return False
    age_seconds = time.time() - lock_path.stat().st_mtime
    return age_seconds > stale_after_seconds


@contextmanager
def _checkpoint_lock(git_dir: Path) -> Iterator[None]:
    lock_path = git_dir / LOCK_FILENAME

    for attempt in range(2):
        try:
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError as exc:
            if attempt == 0 and _is_stale_lock(lock_path):
                lock_path.unlink(missing_ok=True)
                continue
            raise CheckpointError(
                "Checkpoint workflow is locked by another process. "
                "Wait or remove stale lock manually if required."
            ) from exc
        else:
            lock_payload = {
                "pid": os.getpid(),
                "created_at": datetime.now(UTC).isoformat(),
            }
            os.write(fd, json.dumps(lock_payload).encode("utf-8"))
            os.close(fd)
            break
    else:
        raise CheckpointError("Failed to acquire checkpoint workflow lock")

    try:
        yield
    finally:
        lock_path.unlink(missing_ok=True)


def get_session_path(repo_root: Path | None = None) -> Path:
    """Return absolute path to the checkpoint session file in .git."""
    resolved_root = _resolve_repo_root(repo_root)
    git_dir = _resolve_git_dir(resolved_root)
    return git_dir / SESSION_FILENAME


def get_checkpoint_status(repo_root: Path | None = None) -> CheckpointStatus:
    """Inspect active checkpoint session and lock state for repository."""
    resolved_root = _resolve_repo_root(repo_root)
    git_dir = _resolve_git_dir(resolved_root)
    session_path = git_dir / SESSION_FILENAME
    lock_path = git_dir / LOCK_FILENAME

    issues: list[str] = []
    session: CheckpointSession | None = None
    active_session = session_path.exists()
    if active_session:
        try:
            payload = json.loads(session_path.read_text(encoding="utf-8"))
            session = _session_from_payload(payload)
        except json.JSONDecodeError:
            issues.append("Checkpoint session file is corrupted")
        except CheckpointError as exc:
            issues.append(str(exc))

    return CheckpointStatus(
        active_session=active_session,
        session=session,
        session_path=str(session_path),
        lock_present=lock_path.exists(),
        lock_stale=_is_stale_lock(lock_path),
        issues=issues,
    )


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

    return _session_from_payload(payload)


def start_checkpoint(
    repo_root: Path | None = None,
    *,
    allow_sensitive_autocommit: bool = False,
    git_timeout_seconds: int = DEFAULT_GIT_TIMEOUT_SECONDS,
) -> CheckpointSession:
    """Create a builder checkpoint.

    If the tree is dirty, creates an auto-commit first with message
    ``checkpoint pre-build``.
    """
    resolved_root = _resolve_repo_root(repo_root)
    git_dir = _resolve_git_dir(resolved_root)
    _assert_no_git_operation_in_progress(git_dir)

    session_path = git_dir / SESSION_FILENAME
    with _checkpoint_lock(git_dir):
        if session_path.exists():
            raise CheckpointError("An active builder checkpoint session already exists")

        status_output = _run_git(
            resolved_root,
            ["status", "--porcelain"],
            timeout_seconds=git_timeout_seconds,
        )
        auto_commit_performed = False
        if status_output:
            changed_paths = _parse_status_paths(status_output)
            sensitive_paths = _find_sensitive_paths(changed_paths)
            if sensitive_paths and not allow_sensitive_autocommit:
                preview = ", ".join(sensitive_paths[:5])
                raise CheckpointError(
                    "Sensitive-looking files detected in pending changes "
                    f"({preview}). Re-run with allow_sensitive_autocommit=True "
                    "if you explicitly want to include them in checkpoint commit"
                )

            _run_git(
                resolved_root,
                ["add", "-A"],
                timeout_seconds=git_timeout_seconds,
            )
            _run_git(
                resolved_root,
                ["commit", "-m", CHECKPOINT_COMMIT_MESSAGE],
                timeout_seconds=git_timeout_seconds,
            )
            auto_commit_performed = True

        session = CheckpointSession(
            session_id=str(uuid.uuid4()),
            created_at=datetime.now(UTC).isoformat(),
            base_head_sha=_run_git(
                resolved_root,
                ["rev-parse", "HEAD"],
                timeout_seconds=git_timeout_seconds,
            ),
            base_branch=_run_git(
                resolved_root,
                ["rev-parse", "--abbrev-ref", "HEAD"],
                timeout_seconds=git_timeout_seconds,
            ),
            auto_commit_performed=auto_commit_performed,
        )
        _write_session_atomic(session_path, asdict(session))
        return session


def finalize_checkpoint(
    *,
    action: str,
    confirm_revert: str | None = None,
    repo_root: Path | None = None,
    allow_cross_branch_revert: bool = False,
    git_timeout_seconds: int = DEFAULT_GIT_TIMEOUT_SECONDS,
) -> FinalizeResult:
    """Finalize active checkpoint session by keeping or reverting changes."""
    normalized = action.strip().lower()
    if normalized not in {"keep", "revert"}:
        raise CheckpointError("Invalid action. Use 'keep' or 'revert'")

    resolved_root = _resolve_repo_root(repo_root)
    git_dir = _resolve_git_dir(resolved_root)
    _assert_no_git_operation_in_progress(git_dir)

    session_path = git_dir / SESSION_FILENAME
    with _checkpoint_lock(git_dir):
        session = load_active_session(resolved_root)
        warnings: list[str] = []

        current_branch = _run_git(
            resolved_root,
            ["rev-parse", "--abbrev-ref", "HEAD"],
            timeout_seconds=git_timeout_seconds,
        )
        branch_mismatch = current_branch != session.base_branch
        if branch_mismatch and normalized == "revert" and not allow_cross_branch_revert:
            raise CheckpointError(
                "Current branch differs from checkpoint branch "
                f"('{current_branch}' != '{session.base_branch}'). "
                "Revert blocked by default; pass allow_cross_branch_revert=True to force revert."
            )

        if branch_mismatch:
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

        _run_git(
            resolved_root,
            ["reset", "--hard", session.base_head_sha],
            timeout_seconds=git_timeout_seconds,
        )
        _run_git(
            resolved_root,
            ["clean", "-fd"],
            timeout_seconds=git_timeout_seconds,
        )
        session_path.unlink(missing_ok=True)

        return FinalizeResult(
            action="revert",
            reverted_to_sha=session.base_head_sha,
            warnings=warnings,
        )
