"""Safe subprocess execution helper for tools."""

from __future__ import annotations

import subprocess
from typing import Any


def run_command(
    args: list[str],
    *,
    cwd: str | None = None,
    timeout: int = 120,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Run a command and return structured output.

    Never exposes shell=True to avoid injection risks.
    """
    try:
        proc = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
            env=env,
        )
        return {
            "exit_code": proc.returncode,
            "stdout": proc.stdout[-5000:] if len(proc.stdout) > 5000 else proc.stdout,
            "stderr": proc.stderr[-2000:] if len(proc.stderr) > 2000 else proc.stderr,
            "success": proc.returncode == 0,
            "truncated": len(proc.stdout) > 5000 or len(proc.stderr) > 2000,
        }
    except subprocess.TimeoutExpired:
        return {
            "exit_code": -1,
            "stdout": "",
            "stderr": f"Command timed out after {timeout}s",
            "success": False,
            "truncated": False,
        }
    except FileNotFoundError:
        return {
            "exit_code": -1,
            "stdout": "",
            "stderr": f"Command not found: {args[0]}",
            "success": False,
            "truncated": False,
        }
