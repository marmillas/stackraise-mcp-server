"""Bootstrap a project with MCP configuration files."""

from __future__ import annotations

from pathlib import Path

import click
from jinja2 import Environment, PackageLoader

from abstract_backend_mcp.bootstrap.detect_project import detect_project
from abstract_backend_mcp.core.logging import get_logger

logger = get_logger()

_TEMPLATE_FILES = {
    "env.j2": ".env.example",
    "mcp.project.yaml.j2": "mcp.project.yaml",
    "AGENTS.md.j2": "AGENTS.md",
    "opencode.jsonc.j2": "opencode.jsonc",
    "PROJECT.md.j2": "PROJECT.md",
}


def run_init(target_dir: str = ".", dry_run: bool = False) -> list[str]:
    """Generate bootstrap files in *target_dir*.

    Returns list of file paths that were written (or would be written in dry-run).
    """
    root = Path(target_dir).resolve()
    info = detect_project(root)

    env = Environment(
        loader=PackageLoader("abstract_backend_mcp", "templates"),
        keep_trailing_newline=True,
    )

    written: list[str] = []
    for template_name, output_name in _TEMPLATE_FILES.items():
        dest = root / output_name
        if dest.exists():
            click.echo(f"  SKIP {output_name} (already exists)")
            continue

        tmpl = env.get_template(template_name)
        content = tmpl.render(**info)

        if dry_run:
            click.echo(f"  DRY-RUN would create {output_name}")
        else:
            dest.write_text(content)
            click.echo(f"  CREATED {output_name}")

        written.append(str(dest))

    if not written:
        click.echo("Nothing to generate – all files already exist.")
    return written
