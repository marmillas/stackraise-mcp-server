"""Tests for PROJECT.md instructions loading."""

import textwrap

from abstract_backend_mcp.core.instructions import (
    ProjectInstructions,
    _parse_frontmatter,
    load_project_instructions,
)


def test_parse_frontmatter_full():
    content = textwrap.dedent("""\
    ---
    name: my-app
    stack:
      - FastAPI
      - MongoDB
    description: An API for documents
    ---

    ## Objetivo

    Build a document API.
    """)
    fm, body = _parse_frontmatter(content)
    assert fm["name"] == "my-app"
    assert fm["stack"] == ["FastAPI", "MongoDB"]
    assert "## Objetivo" in body


def test_parse_frontmatter_missing():
    content = "## Just markdown\n\nNo frontmatter here."
    fm, body = _parse_frontmatter(content)
    assert fm == {}
    assert "## Just markdown" in body


def test_parse_frontmatter_invalid_yaml():
    content = "---\n: invalid: yaml: {{{\n---\nBody text."
    fm, body = _parse_frontmatter(content)
    assert fm == {}
    assert body == "Body text."


def test_load_with_frontmatter(tmp_path):
    (tmp_path / "PROJECT.md").write_text(textwrap.dedent("""\
    ---
    name: test-proj
    stack: [FastAPI]
    conventions:
      - Use Pydantic
    description: A test project
    ---

    ## Goal

    Test the instructions loader.
    """))
    pi = load_project_instructions(str(tmp_path))
    assert pi.name == "test-proj"
    assert pi.stack == ["FastAPI"]
    assert pi.conventions == ["Use Pydantic"]
    assert pi.description == "A test project"
    assert "## Goal" in pi.instructions


def test_load_without_frontmatter(tmp_path):
    (tmp_path / "PROJECT.md").write_text("## Just instructions\n\nDo stuff.")
    pi = load_project_instructions(str(tmp_path))
    assert pi.name is None
    assert pi.stack == []
    assert "## Just instructions" in pi.instructions


def test_load_file_missing(tmp_path):
    pi = load_project_instructions(str(tmp_path))
    assert pi.instructions != ""
    # Should have default instructions
    assert "Backend MCP server" in pi.instructions


def test_load_custom_filename(tmp_path):
    (tmp_path / "CUSTOM.md").write_text("---\nname: custom\n---\nCustom body.")
    pi = load_project_instructions(str(tmp_path), "CUSTOM.md")
    assert pi.name == "custom"
    assert "Custom body" in pi.instructions


def test_build_server_instructions_full():
    pi = ProjectInstructions(
        name="proj",
        stack=["FastAPI", "MongoDB"],
        conventions=["Use Pydantic"],
        description="A cool project",
        instructions="## Goal\n\nBuild things.",
    )
    text = pi.build_server_instructions()
    assert "Project: A cool project" in text
    assert "Stack: FastAPI, MongoDB" in text
    assert "- Use Pydantic" in text
    assert "## Goal" in text


def test_build_server_instructions_empty():
    pi = ProjectInstructions()
    text = pi.build_server_instructions()
    assert "Backend MCP server" in text
