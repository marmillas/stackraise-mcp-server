"""CLI end-to-end tests for builder-checkpoint commands."""

from __future__ import annotations

import json
import subprocess
import sys
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


def test_cli_run_success_closes_session(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    runner = CliRunner()
    write_changed_cmd = (
        "from pathlib import Path; "
        "Path('sample.txt').write_text('changed\\n', encoding='utf-8')"
    )

    run_cmd = runner.invoke(
        cli,
        [
            "builder-checkpoint",
            "run",
            "--on-success",
            "keep",
            "--on-failure",
            "keep",
            "--repo-root",
            str(repo),
            "--",
            sys.executable,
            "-c",
            write_changed_cmd,
        ],
    )

    assert run_cmd.exit_code == 0
    status = runner.invoke(cli, ["builder-checkpoint", "status", "--repo-root", str(repo)])
    assert status.exit_code == 0
    assert "Active session: no" in status.output
    assert (repo / "sample.txt").read_text(encoding="utf-8") == "changed\n"


def test_cli_run_failure_reverts_and_returns_nonzero(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    runner = CliRunner()
    write_and_fail_cmd = (
        "from pathlib import Path; "
        "Path('sample.txt').write_text('temp\\n', encoding='utf-8'); "
        "raise SystemExit(1)"
    )

    run_cmd = runner.invoke(
        cli,
        [
            "builder-checkpoint",
            "run",
            "--on-success",
            "keep",
            "--on-failure",
            "revert",
            "--confirm-revert",
            "REVERTIR",
            "--repo-root",
            str(repo),
            "--",
            sys.executable,
            "-c",
            write_and_fail_cmd,
        ],
    )

    assert run_cmd.exit_code != 0
    assert "Checkpoint finalize was still executed" in run_cmd.output
    status = runner.invoke(cli, ["builder-checkpoint", "status", "--repo-root", str(repo)])
    assert status.exit_code == 0
    assert "Active session: no" in status.output
    assert (repo / "sample.txt").read_text(encoding="utf-8") == "base\n"


def test_cli_run_ask_fails_in_non_interactive_mode(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    runner = CliRunner()

    run_cmd = runner.invoke(
        cli,
        [
            "builder-checkpoint",
            "run",
            "--on-success",
            "ask",
            "--on-failure",
            "keep",
            "--repo-root",
            str(repo),
            "--",
            sys.executable,
            "-c",
            "print('ok')",
        ],
    )

    assert run_cmd.exit_code != 0
    assert "cannot be 'ask' in non-interactive mode" in run_cmd.output


def test_cli_sync_opencode_policy_updates_and_is_idempotent(tmp_path: Path) -> None:
    opencode_path = tmp_path / "opencode.jsonc"
    opencode_path.write_text(
        json.dumps(
            {
                "agent": {
                    "audit": {
                        "description": "audit",
                        "prompt": "base audit prompt",
                        "tools": {"write": False, "edit": False},
                    },
                    "build": {
                        "description": "build",
                        "prompt": "base build prompt",
                        "tools": {"write": True, "edit": True},
                    },
                    "fix": {
                        "description": "fix",
                        "prompt": "base fix prompt",
                        "tools": {"write": True, "edit": True},
                    },
                    "doc": {
                        "description": "doc",
                        "prompt": "base doc prompt",
                        "tools": {"write": True, "edit": True},
                    },
                    "plan": {
                        "description": "plan",
                        "prompt": "base plan prompt",
                        "tools": {"write": False, "edit": False},
                    }
                }
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    runner = CliRunner()

    first = runner.invoke(
        cli,
        ["sync-opencode-policy", "--opencode-path", str(opencode_path)],
    )
    assert first.exit_code == 0
    assert "Updated: yes" in first.output
    assert "Updated roles: audit, build, fix, doc, plan" in first.output
    synced_text = opencode_path.read_text(encoding="utf-8")
    assert "## Multi-agent collaboration contract" in synced_text
    assert "### Role boundary addendum (audit)" in synced_text
    assert "### Role boundary addendum (build)" in synced_text

    second = runner.invoke(
        cli,
        ["sync-opencode-policy", "--opencode-path", str(opencode_path)],
    )
    assert second.exit_code == 0
    assert "already up to date" in second.output
    assert "Updated: no" in second.output


def test_cli_sync_opencode_policy_creates_missing_file(tmp_path: Path) -> None:
    opencode_path = tmp_path / "nested" / "opencode.jsonc"
    runner = CliRunner()

    result = runner.invoke(
        cli,
        ["sync-opencode-policy", "--opencode-path", str(opencode_path)],
    )

    assert result.exit_code == 0
    assert "Created: yes" in result.output
    assert opencode_path.exists()
    created_text = opencode_path.read_text(encoding="utf-8")
    assert "## Multi-agent collaboration contract" in created_text
