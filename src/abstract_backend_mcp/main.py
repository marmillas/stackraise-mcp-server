"""CLI entry-point for abstract-backend-mcp."""

from __future__ import annotations

import subprocess
from pathlib import Path

import click

from abstract_backend_mcp.core.logging import get_logger

logger = get_logger()


@click.group()
def cli() -> None:
    """abstract-mcp – reusable MCP server for Python backends."""


@cli.command()
@click.option("--config", "config_file", default=None, help="Path to YAML config file.")
def serve(config_file: str | None) -> None:
    """Start the MCP server (stdio transport)."""
    from abstract_backend_mcp.core.server import create_server
    from abstract_backend_mcp.core.settings import MCPSettings

    kwargs: dict[str, str] = {}
    if config_file:
        kwargs["config_file"] = config_file

    settings = MCPSettings(**kwargs)  # type: ignore[arg-type]
    server = create_server(settings)

    logger.info("Starting MCP server in stdio mode…")
    server.run(transport="stdio")


@cli.command()
@click.option("--dry-run", is_flag=True, help="Show what would be generated without writing.")
@click.option("--target", default=".", help="Target project directory.")
def init(dry_run: bool, target: str) -> None:
    """Bootstrap MCP configuration in a project."""
    from abstract_backend_mcp.bootstrap.init_project import run_init

    run_init(target_dir=target, dry_run=dry_run)


@cli.group("builder-checkpoint")
def builder_checkpoint() -> None:
    """Manage builder checkpoint sessions."""


@builder_checkpoint.command("start")
@click.option("--repo-root", default=".", help="Git repository root or child path.")
@click.option(
    "--allow-sensitive-autocommit",
    is_flag=True,
    default=False,
    help="Allow auto-commit even when sensitive-looking paths are detected.",
)
@click.option(
    "--git-timeout-seconds",
    default=30,
    show_default=True,
    type=int,
    help="Timeout in seconds for each git command.",
)
def builder_checkpoint_start(
    repo_root: str,
    allow_sensitive_autocommit: bool,
    git_timeout_seconds: int,
) -> None:
    """Create a checkpoint before builder edits."""
    from abstract_backend_mcp.core.builder_checkpoint import (
        CHECKPOINT_COMMIT_MESSAGE,
        CheckpointError,
        start_checkpoint,
    )

    try:
        session = start_checkpoint(
            Path(repo_root),
            allow_sensitive_autocommit=allow_sensitive_autocommit,
            git_timeout_seconds=git_timeout_seconds,
        )
    except CheckpointError as exc:
        raise click.ClickException(str(exc)) from exc

    click.echo(f"Checkpoint session created: {session.session_id}")
    click.echo(f"Base branch: {session.base_branch}")
    click.echo(f"Base SHA: {session.base_head_sha}")
    if session.auto_commit_performed:
        click.echo(f"Auto-commit created with message: '{CHECKPOINT_COMMIT_MESSAGE}'")


@builder_checkpoint.command("finalize")
@click.option("--action", type=click.Choice(["keep", "revert"]), required=True)
@click.option(
    "--confirm-revert",
    default="",
    help="Required literal value for revert action: REVERTIR",
)
@click.option("--repo-root", default=".", help="Git repository root or child path.")
@click.option(
    "--allow-cross-branch-revert",
    is_flag=True,
    default=False,
    help="Allow revert even if current branch differs from checkpoint branch.",
)
@click.option(
    "--git-timeout-seconds",
    default=30,
    show_default=True,
    type=int,
    help="Timeout in seconds for each git command.",
)
def builder_checkpoint_finalize(
    action: str,
    confirm_revert: str,
    repo_root: str,
    allow_cross_branch_revert: bool,
    git_timeout_seconds: int,
) -> None:
    """Finalize checkpoint by keeping or reverting changes."""
    from abstract_backend_mcp.core.builder_checkpoint import (
        CheckpointError,
        finalize_checkpoint,
    )

    try:
        result = finalize_checkpoint(
            action=action,
            confirm_revert=confirm_revert,
            repo_root=Path(repo_root),
            allow_cross_branch_revert=allow_cross_branch_revert,
            git_timeout_seconds=git_timeout_seconds,
        )
    except CheckpointError as exc:
        raise click.ClickException(str(exc)) from exc

    click.echo(f"Checkpoint finalized with action: {result.action}")
    if result.reverted_to_sha:
        click.echo(f"Repository reverted to: {result.reverted_to_sha}")
    for warning in result.warnings:
        click.echo(f"Warning: {warning}")


@builder_checkpoint.command("status")
@click.option("--repo-root", default=".", help="Git repository root or child path.")
def builder_checkpoint_status(repo_root: str) -> None:
    """Show active checkpoint status and lock details."""
    from abstract_backend_mcp.core.builder_checkpoint import (
        CheckpointError,
        get_checkpoint_status,
    )

    try:
        status = get_checkpoint_status(Path(repo_root))
    except CheckpointError as exc:
        raise click.ClickException(str(exc)) from exc

    click.echo(f"Active session: {'yes' if status.active_session else 'no'}")
    click.echo(f"Session path: {status.session_path}")
    click.echo(f"Lock present: {'yes' if status.lock_present else 'no'}")
    if status.lock_present:
        click.echo(f"Lock stale: {'yes' if status.lock_stale else 'no'}")

    if status.session is not None:
        click.echo(f"Session ID: {status.session.session_id}")
        click.echo(f"Base branch: {status.session.base_branch}")
        click.echo(f"Base SHA: {status.session.base_head_sha}")
        auto_commit_label = "yes" if status.session.auto_commit_performed else "no"
        click.echo(f"Auto-commit performed: {auto_commit_label}")

    for issue in status.issues:
        click.echo(f"Issue: {issue}")


@builder_checkpoint.command("run")
@click.option(
    "--on-success",
    type=click.Choice(["keep", "revert", "ask"]),
    default="ask",
    show_default=True,
    help="Finalize action after successful wrapped command.",
)
@click.option(
    "--on-failure",
    type=click.Choice(["keep", "revert", "ask"]),
    default="ask",
    show_default=True,
    help="Finalize action after failing wrapped command.",
)
@click.option(
    "--confirm-revert",
    default="",
    help="Required literal value for revert action: REVERTIR",
)
@click.option("--repo-root", default=".", help="Git repository root or child path.")
@click.option(
    "--allow-cross-branch-revert",
    is_flag=True,
    default=False,
    help="Allow revert even if current branch differs from checkpoint branch.",
)
@click.option(
    "--allow-sensitive-autocommit",
    is_flag=True,
    default=False,
    help="Allow auto-commit even when sensitive-looking paths are detected.",
)
@click.option(
    "--git-timeout-seconds",
    default=30,
    show_default=True,
    type=int,
    help="Timeout in seconds for each git command.",
)
@click.argument("command", nargs=-1, type=str)
def builder_checkpoint_run(
    on_success: str,
    on_failure: str,
    confirm_revert: str,
    repo_root: str,
    allow_cross_branch_revert: bool,
    allow_sensitive_autocommit: bool,
    git_timeout_seconds: int,
    command: tuple[str, ...],
) -> None:
    """Run a command under transactional checkpoint flow."""
    from abstract_backend_mcp.core.builder_checkpoint import (
        CheckpointError,
        finalize_checkpoint,
        start_checkpoint,
    )

    if not command:
        raise click.ClickException("No command provided. Use: builder-checkpoint run -- <command>")

    stdin_stream = click.get_text_stream("stdin")
    interactive = stdin_stream.isatty()
    if "ask" in {on_success, on_failure} and not interactive:
        raise click.ClickException(
            "on-success/on-failure cannot be 'ask' in non-interactive mode. "
            "Use explicit keep/revert values."
        )

    run_failed = False
    command_exit_code = 0
    finalize_error: CheckpointError | None = None
    start_ok = False

    try:
        start_checkpoint(
            Path(repo_root),
            allow_sensitive_autocommit=allow_sensitive_autocommit,
            git_timeout_seconds=git_timeout_seconds,
        )
        start_ok = True

        proc = subprocess.run(list(command), cwd=Path(repo_root), check=False)
        command_exit_code = proc.returncode
        run_failed = command_exit_code != 0
    except CheckpointError as exc:
        raise click.ClickException(str(exc)) from exc
    except OSError as exc:
        run_failed = True
        command_exit_code = 127
        raise click.ClickException(f"Failed to execute wrapped command: {exc}") from exc
    finally:
        if start_ok:
            selected = on_failure if run_failed else on_success
            action = selected
            if selected == "ask":
                action = click.prompt(
                    "Checkpoint finalize action",
                    type=click.Choice(["keep", "revert"]),
                    default="keep",
                    show_choices=True,
                )

            effective_confirm_revert = confirm_revert
            if action == "revert" and not effective_confirm_revert:
                if interactive:
                    effective_confirm_revert = click.prompt(
                        "Type REVERTIR to confirm revert",
                        default="",
                        show_default=False,
                    )
                else:
                    finalize_error = CheckpointError(
                        "Revert selected in non-interactive mode without --confirm-revert REVERTIR"
                    )

            if finalize_error is None:
                try:
                    finalize_checkpoint(
                        action=action,
                        confirm_revert=effective_confirm_revert,
                        repo_root=Path(repo_root),
                        allow_cross_branch_revert=allow_cross_branch_revert,
                        git_timeout_seconds=git_timeout_seconds,
                    )
                except CheckpointError as exc:
                    finalize_error = exc

    if finalize_error is not None:
        raise click.ClickException(
            f"Wrapped command finished but finalize failed: {finalize_error}"
        )

    if run_failed:
        raise click.ClickException(
            f"Wrapped command exited with non-zero status ({command_exit_code}). "
            "Checkpoint finalize was still executed."
        )


@cli.command("sync-opencode-policy")
@click.option(
    "--opencode-path",
    default="opencode.jsonc",
    show_default=True,
    help="Path to local opencode.jsonc file.",
)
@click.option(
    "--create-if-missing/--no-create-if-missing",
    default=True,
    show_default=True,
    help="Create opencode.jsonc from template if missing.",
)
def sync_opencode_policy(opencode_path: str, create_if_missing: bool) -> None:
    """Synchronize local opencode build prompt with versioned checkpoint policy."""
    from abstract_backend_mcp.core.opencode_policy_sync import (
        OpencodePolicySyncError,
        sync_opencode_build_policy,
    )

    try:
        result = sync_opencode_build_policy(
            Path(opencode_path),
            create_if_missing=create_if_missing,
        )
    except OpencodePolicySyncError as exc:
        raise click.ClickException(str(exc)) from exc

    click.echo(result.message)
    click.echo(f"Path: {result.path}")
    click.echo(f"Created: {'yes' if result.created else 'no'}")
    click.echo(f"Updated: {'yes' if result.updated else 'no'}")


if __name__ == "__main__":
    cli()
