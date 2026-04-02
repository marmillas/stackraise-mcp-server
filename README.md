# abstract-backend-mcp

Reusable MCP server for Python backend development with FastAPI, MongoDB and Stackraise support.

## Features

- **Health & diagnostics** – ping, runtime config, project health checks
- **Test runner** – pytest via Poetry (all, by file, keyword, node-id)
- **Quality tools** – ruff check, ruff format, pyright, combined suite
- **FastAPI introspection** – list routes, find routes, OpenAPI summary
- **MongoDB operations** – readonly inspection + permission-controlled writes
- **Stackraise context** – module detection, domain models, auth scopes, workflows, context snapshots
- **Bootstrap CLI** – auto-generate config files for any Python backend

## Requirements

- Python >= 3.12
- Poetry

## Installation

```bash
# Clone and install
git clone <repo-url> abstract-backend-mcp
cd abstract-backend-mcp
poetry install
```

## Quick Start

```bash
# Bootstrap MCP config in your project
cd /path/to/your-project
poetry run abstract-mcp init

# Start MCP server (stdio transport)
poetry run abstract-mcp serve

# With a YAML config override
poetry run abstract-mcp serve --config mcp.project.yaml
```

## Usage: How to Connect the MCP to Your Project

There are three ways to use this MCP server, from lightest to most integrated:

### Option A: Reference from your MCP client (recommended, zero coupling)

The MCP lives in its own repo. Your project only needs a client config file (e.g. `opencode.jsonc`, VS Code MCP settings, etc.) pointing to it:

```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "abstract-mcp": {
      "type": "local",
      "command": [
        "poetry",
        "-C",
        "/path/to/coding-mcp",
        "run",
        "abstract-mcp",
        "serve",
        "--config",
        "/path/to/your-project/mcp.project.yaml"
      ],
      "enabled": true,
      "environment": {
        "PROJECT_NAME": "my-app",
        "PROJECT_ROOT": "/path/to/your-project",
        "FASTAPI_APP_PATH": "src.main:app"
      }
    }
  }
}
```

**Pros**: no dependency added to your project, one MCP repo serves multiple projects.
**Cons**: every dev needs the MCP repo cloned locally at a known path.

### Option B: Install as a local dev dependency

From your project directory:

```bash
poetry add --group dev /path/to/coding-mcp
```

Then you can run the CLI directly inside your project:

```bash
poetry run abstract-mcp init     # generate config files
poetry run abstract-mcp serve    # start MCP server
```

And point your client config to the project itself:

```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "abstract-mcp": {
      "type": "local",
      "command": ["poetry", "run", "abstract-mcp", "serve"],
      "enabled": true
    }
  }
}
```

**Pros**: self-contained, any dev can run `poetry install` and it works.
**Cons**: adds a dev dependency; linked to a local path (or needs a registry).

### Option C: Publish to a private registry (teams)

```bash
cd /path/to/coding-mcp
poetry build
poetry publish --repository your-private-registry
```

Then in any project:

```bash
poetry add --group dev abstract-backend-mcp
```

**Pros**: versioned, no local path coupling.
**Cons**: requires a package registry.

### Multiple projects simultaneously

Each client session spawns its own MCP process (stdio transport = 1 process per connection). You can run multiple projects at the same time without conflicts — each has its own config and its own process.

### Typical workflow

```
1. Clone coding-mcp once on your machine
2. In your target project:
   a. Create a mcp.project.yaml with project-specific settings
   b. Point your MCP client to the server (option A, B, or C)
3. Start your client (OpenCode, VS Code, Copilot CLI, etc.)
4. The MCP exposes all configured tools to the agent
```

## Configuration

Settings are loaded from (in order of priority):

1. Environment variables
2. `.env` file
3. YAML config file (via `--config` or `CONFIG_FILE` env var)
4. Built-in defaults

### Key settings

| Variable | Default | Description |
|---|---|---|
| `PROJECT_NAME` | `my-project` | Project identifier |
| `ENVIRONMENT` | `development` | Current environment |
| `FASTAPI_APP_PATH` | `app.main:app` | Python import path of the FastAPI app |
| `MONGODB_URI` | `mongodb://localhost:27017` | MongoDB connection string |
| `MONGODB_SAMPLE_MAX_DOCUMENTS` | `20` | Maximum number of sampled documents returned by MongoDB tools |
| `MONGODB_SAMPLE_MAX_BYTES` | `65536` | Maximum total bytes returned by `sample_documents` |
| `MONGODB_SAMPLE_MAX_FIELD_CHARS` | `2000` | Max characters preserved per string field in sampled documents |
| `ENABLE_FASTAPI_TOOLS` | `true` | Enable FastAPI tools |
| `ALLOW_FASTAPI_RUNTIME_IMPORTS` | `false` | Allow importing FastAPI runtime app for route/OpenAPI inspection |
| `ENABLE_MONGODB_TOOLS` | `true` | Enable MongoDB tools |
| `ENABLE_STACKRAISE_TOOLS` | `false` | Enable Stackraise tools |
| `ENABLE_DEEP_STACKRAISE_CONTEXT` | `true` | Enable deep module/symbol indexing |
| `ALLOW_WRITE_OPERATIONS` | `false` | Allow MongoDB writes |
| `REQUIRE_WRITE_CONFIRMATION` | `true` | Require explicit `confirmed=True` |
| `ALLOWED_WRITE_COLLECTIONS` | `[]` | Collection allowlist (empty = all) |
| `STACKRAISE_CONTEXT_MODE` | `hybrid` | Extraction mode: `static`, `runtime`, `hybrid` |
| `ALLOW_RUNTIME_CONTEXT_IMPORTS` | `false` | Allow live runtime imports during context extraction |
| `STACKRAISE_MODULE_ROOTS` | `[]` | Optional glob roots for Stackraise packages |
| `MAX_SOURCE_CHUNK_LINES` | `200` | Max lines returned by source-oriented tools |
| `MAX_TOTAL_SNAPSHOT_ITEMS` | `500` | Global cap for deep snapshot inventories |
| `MAX_OUTPUT_ITEMS` | `50` | Max items returned by paginated Stackraise tools |
| `STACKRAISE_SEARCH_MAX_PATTERN_LENGTH` | `200` | Max accepted length for `search_stackraise_code` pattern |
| `STACKRAISE_SEARCH_TIMEOUT_MS` | `500` | Search timeout budget in milliseconds |
| `STACKRAISE_SEARCH_MAX_SCANNED_LINES` | `20000` | Max total scanned lines for code search |
| `STACKRAISE_CONTEXT_CACHE_TTL_SECONDS` | `30` | Cache TTL for Stackraise context provider |
| `STACKRAISE_CONTEXT_CACHE_MAX_ENTRIES` | `32` | Max in-memory context cache entries |
| `STACKRAISE_CONTEXT_FINGERPRINT_TTL_SECONDS` | `1` | TTL for project fingerprint reuse before rescanning files |
| `REDACT_SENSITIVE_FIELDS` | `true` | Redact secrets in all output |
| `PROJECT_INSTRUCTIONS_FILE` | `PROJECT.md` | Path to project instructions file |

### Cache profile recommendations

- **High precision profile** (always reflect file changes quickly):
  - `STACKRAISE_CONTEXT_FINGERPRINT_TTL_SECONDS=0`
  - `STACKRAISE_CONTEXT_CACHE_TTL_SECONDS=0`
- **Balanced profile** (default, better performance):
  - `STACKRAISE_CONTEXT_FINGERPRINT_TTL_SECONDS=1`
  - `STACKRAISE_CONTEXT_CACHE_TTL_SECONDS=30`

Use the high precision profile when actively editing many modules and you need the most
up-to-date snapshot on every request.

## Project Instructions (PROJECT.md)

Each project can define a `PROJECT.md` file that the MCP reads at startup and passes as context to the agent. This replaces the generic default instructions with project-specific goals, architecture notes, and conventions.

### Format

The file uses YAML frontmatter (optional) + markdown body:

```markdown
---
name: my-app
description: Document management API with electronic signatures
stack:
  - FastAPI
  - MongoDB
  - Stackraise
conventions:
  - Use Pydantic for all validation
  - Tests required for every endpoint
  - Spanish comments in domain code
---

## Objetivo

REST API for document management with workflow automation...

## Arquitectura

- backend/src/demo/ contains the main app
- Domain models in domain/
- Services in service/

## Notas para el agente

- Do not modify auth fixtures without confirmation
- Integration tests require MongoDB running locally
```

### How it works

1. On startup, the MCP reads `PROJECT.md` (or the file configured in `PROJECT_INSTRUCTIONS_FILE`) from the project root
2. The frontmatter metadata (name, stack, conventions, description) is formatted and prepended
3. The markdown body is included as the main instructions
4. The combined text is passed to the MCP server as `instructions`, which the agent receives as context

### Behavior

| Scenario | Result |
|---|---|
| `PROJECT.md` exists with frontmatter + body | Full instructions with metadata |
| `PROJECT.md` exists without frontmatter | Entire file used as instructions |
| `PROJECT.md` does not exist | Generic default instructions |
| Invalid YAML frontmatter | Warning logged, body used as instructions |

### Generation

Running `abstract-mcp init` generates a `PROJECT.md` template with detected stack info and placeholder sections.

### Runtime access

The tool `show_project_instructions` lets the agent re-read the parsed PROJECT.md at any time during a session.

## Tools

### Health
- `ping` – server alive check
- `show_runtime_config` – sanitized settings
- `list_enabled_tools` – active tool groups
- `check_project_health` – project structure detection

### Tests & Quality
- `run_tests_all`, `run_tests_file`, `run_tests_keyword`, `run_tests_nodeid`
- `run_ruff_check`, `run_ruff_format_check`, `run_pyright`, `run_quality_suite`

### FastAPI
- `list_routes`, `find_route`, `show_openapi_summary`

When `ALLOW_FASTAPI_RUNTIME_IMPORTS=false`, FastAPI introspection tools return a blocked error envelope.

### MongoDB
- **Readonly**: `list_collections`, `sample_documents`, `count_documents`, `show_indexes`
- **Writes**: `insert_one_controlled`, `update_one_controlled`, `delete_one_controlled`

MongoDB sample responses are bounded by `MONGODB_SAMPLE_MAX_DOCUMENTS` and respect
`REDACT_SENSITIVE_FIELDS` for textual/key-based redaction.
Additionally, payload size is bounded by `MONGODB_SAMPLE_MAX_BYTES` and large string
fields are truncated according to `MONGODB_SAMPLE_MAX_FIELD_CHARS`.

### Stackraise
- `detect_stackraise`, `show_stackraise_modules`
- `show_stackraise_db_metadata`, `show_stackraise_auth_scopes`
- `list_stackraise_crud_resources`, `list_stackraise_workflows`
- `list_stackraise_module_tree`, `list_stackraise_modules`
- `show_stackraise_module_symbols`, `show_stackraise_symbol_source`
- `read_stackraise_module_chunk`, `search_stackraise_code` (`use_regex=false` by default)
- `build_stackraise_context_snapshot` – full context with schema:
  - `project`, `stackraise.modules`, `stackraise.domain`, `stackraise.api`
  - `stackraise.auth`, `stackraise.workflows`, `stackraise.frontend_contracts`
  - `security` (redacted, warnings), `extraction` (mode, fallback, warnings)

### Recommended Stackraise flow

Use navigation in this order to keep responses compact and deterministic:

1. `build_stackraise_context_snapshot(mode="hybrid")`
2. `list_stackraise_module_tree()`
3. `show_stackraise_module_symbols(module="stackraise.some_module")`
4. `show_stackraise_symbol_source(symbol_id="...")` or `read_stackraise_module_chunk(...)`

For large codebases, prefer bounded tree navigation with
`list_stackraise_module_tree(parent_module="stackraise", depth=0, limit=50)`.
By default, `list_stackraise_module_tree` uses `depth=0` to avoid returning deep subtrees.

This workflow follows `snapshot -> tree -> symbols -> source` and avoids large payloads.

## Write Operation Policy

All MongoDB writes are gated by:

1. `ALLOW_WRITE_OPERATIONS` must be `true`
2. `ENVIRONMENT` must not be `production`/`prod`
3. Collection must be in `ALLOWED_WRITE_COLLECTIONS` (if non-empty)
4. `confirmed=True` must be passed explicitly (when `REQUIRE_WRITE_CONFIRMATION=true`)

## Context Extraction Modes

| Mode | Behavior |
|---|---|
| `static` | AST analysis of source files, no imports |
| `runtime` | Live introspection of imported modules (requires `ALLOW_RUNTIME_CONTEXT_IMPORTS=true`) |
| `hybrid` | Runtime with automatic fallback to static (runtime disabled by policy by default) |

## Secret Redaction

When `REDACT_SENSITIVE_FIELDS=true` (default), context output is redacted in two layers:

- key-based redaction (`password`, `secret`, `token`, `api_key`, etc.)
- textual redaction for symbol/source content (docstrings, literals, bearer/query tokens)

Sensitive values are replaced with `***REDACTED***`.

## OpenCode Integration

After running `abstract-mcp init`, use the generated `opencode.jsonc`:

```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "abstract-mcp": {
      "type": "local",
      "command": ["poetry", "run", "abstract-mcp", "serve"],
      "enabled": true
    }
  }
}
```

The generated `opencode.jsonc` also includes an `agent` block with predefined prompts:

- **audit** – review, quality and security assessment
- **build** – implementation from execution plan
- **fix** – remediation based on audit findings
- **doc** – documentation engineering (Markdown-only edits)
- **plan** – planning and decomposition before implementation

`AGENTS.md` remains a concise operational role reference and is generated alongside
`opencode.jsonc`.

### Builder checkpoint workflow

The CLI includes a checkpoint helper for builder sessions:

- `poetry run abstract-mcp builder-checkpoint start`
- `poetry run abstract-mcp builder-checkpoint run --on-success keep --on-failure ask -- <command ...>`
- `poetry run abstract-mcp builder-checkpoint status`
- `poetry run abstract-mcp builder-checkpoint finalize --action keep`
- `poetry run abstract-mcp builder-checkpoint finalize --action revert --confirm-revert REVERTIR`
- `poetry run abstract-mcp sync-opencode-policy`

Behavior:

- On `start`, if the Git tree is dirty, the command runs `git add -A` and creates
  a local commit with exact message `checkpoint pre-build`.
- If sensitive-looking files are detected in pending changes, `start` blocks by
  default. Use `--allow-sensitive-autocommit` only when explicitly intended.
- It stores checkpoint metadata in `.git/abstract_builder_checkpoint_session.json`
  and uses lock/atomic writes to reduce race and corruption risks.
- `run` is the transactional wrapper that enforces start/execute/finalize flow with
  explicit success/failure policies.
- On `finalize --action revert`, it performs `git reset --hard <base_head_sha>` and
  `git clean -fd` after confirmation.
- Revert is blocked by default if current branch differs from checkpoint branch.
  Override only explicitly with `--allow-cross-branch-revert`.
- `sync-opencode-policy` updates (or creates) local `opencode.jsonc` from versioned
  policy sources, including multi-agent collaboration addendums for
  `audit/build/fix/doc/plan`, so ignored runtime configs remain reproducible.

Recommended operational step after pull/init:

- `poetry run abstract-mcp sync-opencode-policy`

## Limitations (v1)

- No HTTP/SSE transport (stdio only)
- Dependency tracing is static and best-effort (import graph only)
- Stackraise introspection is best-effort and defensive
- No advanced RPA analysis beyond detection
- MongoDB adapter uses pymongo (no async motor)

## Development

```bash
poetry install
poetry run pytest -v
poetry run ruff check .
```
