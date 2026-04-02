"""CLI end-to-end tests for builder-checkpoint commands."""

from __future__ import annotations

import subprocess
from pathlib import Path

from click.testing import CliRunner

from abstract_backend_mcp.main import cli


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


def test_cli_start_status_and_keep(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    runner = CliRunner()

    start = runner.invoke(
        cli,
        ["builder-checkpoint", "start", "--repo-root", str(repo)],
    )
    assert start.exit_code == 0
    assert "Checkpoint session created" in start.output

    status_active = runner.invoke(
        cli,
        ["builder-checkpoint", "status", "--repo-root", str(repo)],
    )
    assert status_active.exit_code == 0
    assert "Active session: yes" in status_active.output

    (repo / "sample.txt").write_text("builder-change\n", encoding="utf-8")
    keep = runner.invoke(
        cli,
        ["builder-checkpoint", "finalize", "--action", "keep", "--repo-root", str(repo)],
    )
    assert keep.exit_code == 0
    assert "action: keep" in keep.output

    status_closed = runner.invoke(
        cli,
        ["builder-checkpoint", "status", "--repo-root", str(repo)],
    )
    assert status_closed.exit_code == 0
    assert "Active session: no" in status_closed.output


def test_cli_revert_requires_confirmation_and_cross_branch_override(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    runner = CliRunner()

    start = runner.invoke(
        cli,
        ["builder-checkpoint", "start", "--repo-root", str(repo)],
    )
    assert start.exit_code == 0

    _run_git(repo, ["checkout", "-b", "other-branch"])
    (repo / "sample.txt").write_text("branch-change\n", encoding="utf-8")

    blocked = runner.invoke(
        cli,
        [
            "builder-checkpoint",
            "finalize",
            "--action",
            "revert",
            "--confirm-revert",
            "REVERTIR",
            "--repo-root",
            str(repo),
        ],
    )
    assert blocked.exit_code != 0
    assert "Revert blocked by default" in blocked.output

    allowed = runner.invoke(
        cli,
        [
            "builder-checkpoint",
            "finalize",
            "--action",
            "revert",
            "--confirm-revert",
            "REVERTIR",
            "--allow-cross-branch-revert",
            "--repo-root",
            str(repo),
        ],
    )
    assert allowed.exit_code == 0
    assert "action: revert" in allowed.output
    assert (repo / "sample.txt").read_text(encoding="utf-8") == "base\n"
