"""Code quality tools (ruff, pyright)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from abstract_backend_mcp.tools.subprocess_helper import run_command

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from abstract_backend_mcp.core.settings import MCPSettings


def register(server: FastMCP, settings: MCPSettings) -> None:
    cwd = settings.project_root

    @server.tool(name="run_ruff_check", description="Run ruff linter on the project.")
    def run_ruff_check() -> dict[str, Any]:
        return run_command(["poetry", "run", "ruff", "check", "."], cwd=cwd)

    @server.tool(
        name="run_ruff_format_check",
        description="Check if code is formatted according to ruff.",
    )
    def run_ruff_format_check() -> dict[str, Any]:
        return run_command(["poetry", "run", "ruff", "format", "--check", "."], cwd=cwd)

    @server.tool(name="run_pyright", description="Run pyright type-checker on the project.")
    def run_pyright() -> dict[str, Any]:
        return run_command(["poetry", "run", "pyright"], cwd=cwd)

    @server.tool(
        name="run_quality_suite",
        description="Run ruff check + ruff format check + pyright in sequence.",
    )
    def run_quality_suite() -> dict[str, Any]:
        results: dict[str, Any] = {}
        results["ruff_check"] = run_command(
            ["poetry", "run", "ruff", "check", "."], cwd=cwd
        )
        results["ruff_format"] = run_command(
            ["poetry", "run", "ruff", "format", "--check", "."], cwd=cwd
        )
        results["pyright"] = run_command(["poetry", "run", "pyright"], cwd=cwd)
        results["all_passed"] = all(r["success"] for r in results.values())
        return results
