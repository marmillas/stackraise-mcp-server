"""Stackraise adapter – progressive, defensive detection of framework features."""

from __future__ import annotations

import importlib
import inspect
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

    def get_runtime_module_metadata(
        self,
        modules: dict[str, bool] | None = None,
    ) -> list[dict[str, Any]]:
        """Return runtime metadata for importable Stackraise modules."""
        module_map = modules or self.detect_modules()
        metadata: list[dict[str, Any]] = []

        for mod_name, available in module_map.items():
            if not available:
                continue

            module_obj = self._get_module(mod_name)
            if module_obj is None:
                continue

            fq_module = f"{self._package}.{mod_name}"
            exports = self._list_module_exports(module_obj)
            metadata.append(
                {
                    "module_id": f"mod:{fq_module}",
                    "module": fq_module,
                    "package": fq_module.rsplit(".", 1)[0],
                    "source": "runtime",
                    "exports": exports,
                    "exports_count": len(exports),
                }
            )

        metadata.sort(key=lambda item: item["module"])
        return metadata

    def get_runtime_symbol_index(
        self,
        modules: dict[str, bool] | None = None,
    ) -> list[dict[str, Any]]:
        """Return symbol metadata discovered from imported modules."""
        module_map = modules or self.detect_modules()
        symbols: list[dict[str, Any]] = []

        for mod_name, available in module_map.items():
            if not available:
                continue

            module_obj = self._get_module(mod_name)
            if module_obj is None:
                continue

            fq_module = f"{self._package}.{mod_name}"
            module_id = f"mod:{fq_module}"
            for symbol_name in self._list_module_exports(module_obj):
                if not hasattr(module_obj, symbol_name):
                    continue

                symbol_obj = getattr(module_obj, symbol_name)
                symbol_kind = self._resolve_symbol_kind(symbol_obj)
                symbol_meta: dict[str, Any] = {
                    "symbol_id": f"sym:runtime:{module_id}:{symbol_name}",
                    "module_id": module_id,
                    "module": fq_module,
                    "name": symbol_name,
                    "qualname": symbol_name,
                    "kind": symbol_kind,
                    "source": "runtime",
                    "line": 0,
                    "end_line": 0,
                    "path": "",
                }

                if inspect.isclass(symbol_obj):
                    symbol_meta["mro"] = [cls.__name__ for cls in symbol_obj.mro()]
                if callable(symbol_obj):
                    symbol_meta["signature"] = self._safe_signature(symbol_obj)

                symbols.append(symbol_meta)

        symbols.sort(key=lambda item: (item["module"], item["name"]))
        return symbols

    def _list_module_exports(self, module_obj: Any) -> list[str]:
        exports = getattr(module_obj, "__all__", None)
        if isinstance(exports, (list, tuple)):
            return sorted(str(item) for item in exports)
        return sorted(name for name in dir(module_obj) if not name.startswith("_"))

    def _resolve_symbol_kind(self, symbol_obj: Any) -> str:
        if inspect.isclass(symbol_obj):
            return "class"
        if inspect.isfunction(symbol_obj):
            return "function"
        if inspect.ismethod(symbol_obj):
            return "method"
        if callable(symbol_obj):
            return "callable"
        return "attribute"

    def _safe_signature(self, symbol_obj: Any) -> str:
        try:
            return str(inspect.signature(symbol_obj))
        except (TypeError, ValueError):
            return ""
