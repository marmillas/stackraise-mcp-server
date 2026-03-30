"""CLI entry-point for abstract-backend-mcp."""

from __future__ import annotations

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


if __name__ == "__main__":
    cli()
