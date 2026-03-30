"""Pydantic schemas for the Stackraise context snapshot."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ModuleTreeNode(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str = ""
    module: str = ""
    module_id: str = ""
    kind: str = ""
    path: str = ""
    children: list[ModuleTreeNode] = Field(default_factory=list)


class ModuleIndexEntry(BaseModel):
    model_config = ConfigDict(extra="allow")

    module_id: str = ""
    module: str = ""
    package: str = ""
    path: str = ""
    kind: str = ""
    source: str = ""
    line_count: int = 0
    hash: str = ""


class SymbolIndexEntry(BaseModel):
    model_config = ConfigDict(extra="allow")

    symbol_id: str = ""
    module_id: str = ""
    module: str = ""
    name: str = ""
    qualname: str = ""
    kind: str = ""
    source: str = ""
    line: int = 0
    end_line: int = 0
    path: str = ""


class DependencyEdgeEntry(BaseModel):
    model_config = ConfigDict(extra="allow")

    edge_id: str = ""
    source_module_id: str = ""
    source_module: str = ""
    target: str = ""
    line: int = 0
    kind: str = ""
    source: str = ""
    internal: bool = False


class ContentChunkEntry(BaseModel):
    model_config = ConfigDict(extra="allow")

    chunk_id: str = ""
    module_id: str = ""
    module: str = ""
    path: str = ""
    source: str = ""
    start_line: int = 0
    end_line: int = 0
    line_count: int = 0
    preview: str = ""


class ProjectContext(BaseModel):
    name: str = ""
    root: str = ""
    environment: str = ""
    has_poetry: bool = False
    has_fastapi: bool = False
    has_mongodb: bool = False
    has_stackraise: bool = False


class StackraiseModules(BaseModel):
    detected: dict[str, bool] = Field(default_factory=dict)
    module_tree: list[ModuleTreeNode] = Field(default_factory=list)
    module_index: list[ModuleIndexEntry] = Field(default_factory=list)
    symbol_index: list[SymbolIndexEntry] = Field(default_factory=list)
    dependency_edges: list[DependencyEdgeEntry] = Field(default_factory=list)
    content_catalog: list[ContentChunkEntry] = Field(default_factory=list)


class DomainContext(BaseModel):
    documents: list[dict[str, Any]] = Field(default_factory=list)
    references: list[str] = Field(default_factory=list)
    collections: list[str] = Field(default_factory=list)
    indexes: list[dict[str, Any]] = Field(default_factory=list)


class APIContext(BaseModel):
    routes: list[dict[str, Any]] = Field(default_factory=list)
    crud_resources: list[dict[str, Any]] = Field(default_factory=list)
    openapi_summary: dict[str, Any] = Field(default_factory=dict)


class AuthContext(BaseModel):
    available: bool = False
    scopes: list[str] = Field(default_factory=list)
    guards: list[str] = Field(default_factory=list)


class WorkflowContext(BaseModel):
    rpa: dict[str, Any] = Field(default_factory=dict)
    email_watcher: dict[str, Any] = Field(default_factory=dict)
    doc_generation: dict[str, Any] = Field(default_factory=dict)


class FrontendContracts(BaseModel):
    detected: bool = False
    packages: list[str] = Field(default_factory=list)
    notes: str = ""


class StackraiseContext(BaseModel):
    modules: StackraiseModules = Field(default_factory=StackraiseModules)
    domain: DomainContext = Field(default_factory=DomainContext)
    api: APIContext = Field(default_factory=APIContext)
    auth: AuthContext = Field(default_factory=AuthContext)
    workflows: WorkflowContext = Field(default_factory=WorkflowContext)
    frontend_contracts: FrontendContracts = Field(default_factory=FrontendContracts)


class SecurityContext(BaseModel):
    redacted: bool = True
    warnings: list[str] = Field(default_factory=list)


class ExtractionMeta(BaseModel):
    mode: str = "hybrid"
    fallback_used: bool = False
    warnings: list[str] = Field(default_factory=list)


class ContextSnapshot(BaseModel):
    project: ProjectContext = Field(default_factory=ProjectContext)
    stackraise: StackraiseContext = Field(default_factory=StackraiseContext)
    security: SecurityContext = Field(default_factory=SecurityContext)
    extraction: ExtractionMeta = Field(default_factory=ExtractionMeta)
