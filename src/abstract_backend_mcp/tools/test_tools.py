"""Test runner tools (pytest via Poetry)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from abstract_backend_mcp.tools.subprocess_helper import run_command

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from abstract_backend_mcp.core.settings import MCPSettings


def register(server: FastMCP, settings: MCPSettings) -> None:
    cwd = settings.project_root

    @server.tool(name="run_tests_all", description="Run all project tests with pytest.")
    def run_tests_all() -> dict[str, Any]:
        return run_command(["poetry", "run", "pytest", "-v", "--tb=short"], cwd=cwd)

    @server.tool(
        name="run_tests_file",
        description="Run tests in a specific file.",
    )
    def run_tests_file(path: str) -> dict[str, Any]:
        return run_command(["poetry", "run", "pytest", "-v", "--tb=short", path], cwd=cwd)

    @server.tool(
        name="run_tests_keyword",
        description="Run tests matching a keyword expression.",
    )
    def run_tests_keyword(keyword: str) -> dict[str, Any]:
        return run_command(
            ["poetry", "run", "pytest", "-v", "--tb=short", "-k", keyword], cwd=cwd
        )

    @server.tool(
        name="run_tests_nodeid",
        description="Run a specific test by its node ID.",
    )
    def run_tests_nodeid(nodeid: str) -> dict[str, Any]:
        return run_command(["poetry", "run", "pytest", "-v", "--tb=short", nodeid], cwd=cwd)
