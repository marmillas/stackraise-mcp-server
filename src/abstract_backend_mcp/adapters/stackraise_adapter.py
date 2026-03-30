"""Stackraise adapter – progressive, defensive detection of framework features."""

from __future__ import annotations

import importlib
from typing import Any

from abstract_backend_mcp.core.logging import get_logger

logger = get_logger()

# Modules that Stackraise may expose
_KNOWN_MODULES = [
    "model",
    "db",
    "ctrl",
    "auth",
    "di",
    "logging",
    "ai",
    "templating",
    "io",
]


class StackraiseAdapter:
    def __init__(self, package_name: str = "stackraise") -> None:
        self._package = package_name
        self._modules: dict[str, Any] = {}
        self._available: bool | None = None

    def is_available(self) -> bool:
        if self._available is not None:
            return self._available
        try:
            importlib.import_module(self._package)
            self._available = True
        except ImportError:
            self._available = False
        return self._available

    def detect_modules(self) -> dict[str, bool]:
        """Return which Stackraise sub-modules are importable."""
        result: dict[str, bool] = {}
        for mod_name in _KNOWN_MODULES:
            fqn = f"{self._package}.{mod_name}"
            try:
                importlib.import_module(fqn)
                result[mod_name] = True
                self._modules[mod_name] = importlib.import_module(fqn)
            except ImportError:
                result[mod_name] = False
        return result

    def _get_module(self, name: str) -> Any | None:
        if name in self._modules:
            return self._modules[name]
        fqn = f"{self._package}.{name}"
        try:
            mod = importlib.import_module(fqn)
            self._modules[name] = mod
            return mod
        except ImportError:
            return None

    def get_db_metadata(self) -> dict[str, Any]:
        db_mod = self._get_module("db")
        if db_mod is None:
            return {"available": False}
        result: dict[str, Any] = {"available": True}
        # Try to find Document subclasses
        document_cls = getattr(db_mod, "Document", None)
        if document_cls:
            result["document_base_class"] = document_cls.__name__
        return result

    def get_logging_metadata(self) -> dict[str, Any]:
        log_mod = self._get_module("logging")
        if log_mod is None:
            return {"available": False}
        return {"available": True, "module": f"{self._package}.logging"}

    def get_di_metadata(self) -> dict[str, Any]:
        di_mod = self._get_module("di")
        if di_mod is None:
            return {"available": False}
        return {"available": True, "module": f"{self._package}.di"}

    def get_auth_metadata(self) -> dict[str, Any]:
        auth_mod = self._get_module("auth")
        if auth_mod is None:
            return {"available": False}
        result: dict[str, Any] = {"available": True}
        # Try to detect scopes/guards
        for attr_name in ("Scope", "Guard", "scopes", "guards"):
            val = getattr(auth_mod, attr_name, None)
            if val is not None:
                result[f"has_{attr_name.lower()}"] = True
        return result

    def list_crud_resources(self) -> list[dict[str, Any]]:
        """Attempt to detect CRUD resources registered via ctrl module."""
        ctrl_mod = self._get_module("ctrl")
        if ctrl_mod is None:
            return []
        # Look for Crud class or registry
        crud_cls = getattr(ctrl_mod, "Crud", None)
        if crud_cls is None:
            return []
        # This is a best-effort detection — depends on Stackraise internals
        return [{"note": "Crud class detected, detailed listing requires runtime introspection"}]

    def get_domain_model_graph(self) -> dict[str, Any]:
        """Return domain model info if detectable."""
        model_mod = self._get_module("model")
        if model_mod is None:
            return {"available": False}
        return {"available": True, "module": f"{self._package}.model"}

    def get_workflow_map(self) -> dict[str, Any]:
        """Detect RPA/AI/IO workflow modules."""
        result: dict[str, Any] = {}
        for mod_name in ("ai", "io", "templating"):
            mod = self._get_module(mod_name)
            result[mod_name] = {"available": mod is not None}
        return result

    def get_frontend_contracts(self) -> dict[str, Any]:
        """Best-effort detection of frontend contracts — requires static analysis."""
        return {"note": "Frontend contract detection requires static file analysis"}
