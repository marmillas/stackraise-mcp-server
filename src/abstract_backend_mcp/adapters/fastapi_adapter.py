"""FastAPI adapter – loads a FastAPI app and exposes route introspection."""

from __future__ import annotations

import importlib
from typing import Any

from abstract_backend_mcp.core.errors import DependencyNotAvailableError
from abstract_backend_mcp.core.logging import get_logger

logger = get_logger()


class FastAPIAdapter:
    def __init__(self, app_path: str) -> None:
        self._app_path = app_path
        self._app: Any | None = None

    def load_app(self) -> Any:
        """Import the FastAPI application from *app_path* ('module.path:attr')."""
        if self._app is not None:
            return self._app

        try:
            module_path, attr = self._app_path.rsplit(":", 1)
            mod = importlib.import_module(module_path)
            self._app = getattr(mod, attr)
        except Exception as exc:
            raise DependencyNotAvailableError(
                f"Could not import FastAPI app from '{self._app_path}': {exc}"
            ) from exc
        return self._app

    def list_routes(self) -> list[dict[str, Any]]:
        app = self.load_app()
        routes: list[dict[str, Any]] = []
        for route in getattr(app, "routes", []):
            if hasattr(route, "methods"):
                routes.append(
                    {
                        "path": getattr(route, "path", ""),
                        "methods": sorted(route.methods) if route.methods else [],
                        "name": getattr(route, "name", None),
                        "tags": getattr(route, "tags", []),
                    }
                )
        return routes

    def find_routes(self, path_fragment: str) -> list[dict[str, Any]]:
        return [r for r in self.list_routes() if path_fragment in r["path"]]

    def get_openapi_summary(self) -> dict[str, Any]:
        app = self.load_app()
        schema_fn = getattr(app, "openapi", None)
        if schema_fn is None:
            return {"error": "App does not expose openapi()"}
        try:
            schema = schema_fn()
            return {
                "title": schema.get("info", {}).get("title", ""),
                "version": schema.get("info", {}).get("version", ""),
                "paths_count": len(schema.get("paths", {})),
                "tags": [t.get("name") for t in schema.get("tags", [])],
            }
        except Exception as exc:
            return {"error": str(exc)}
