# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

epub-utils is a Python library and CLI tool for inspecting EPUB files from the terminal. It supports both EPUB 2.0.1 and EPUB 3.0+ specifications.

## Virtual Environment

The virtual environment name is `epub-utils`.

## Common Commands

```bash
# Run all tests
pytest

# Run a single test file
pytest tests/test_doc.py

# Run a specific test
pytest tests/test_doc.py::test_function_name

# Lint code
ruff check

# Format code
ruff check --select I --fix && ruff format

# Makefile shortcuts
make test      # Run tests
make lint      # Lint code
make format    # Format code
make coverage  # Generate coverage report
```

## Code Style

- Uses ruff for linting and formatting
- Tab indentation, single quotes, 100 character line limit
- Configuration in `ruff.toml`

## Architecture

### Entry Points
- **CLI**: `epub_utils/cli.py` - Click-based CLI with commands: `container`, `package`, `toc`, `metadata`, `manifest`, `spine`, `content`, `files`
- **Library**: `epub_utils.Document` - Main API entry point

### Core Classes (epub_utils/)
- `Document` (`doc.py`): Main class that wraps an EPUB file. Uses lazy loading for all parsed components.
- `Container` (`container.py`): Parses `META-INF/container.xml`, locates the OPF package file.
- `Package` (`package/__init__.py`): Parses the OPF file, contains `Metadata`, `Manifest`, and `Spine`.
- `Metadata` (`package/metadata.py`): Dublin Core metadata (title, creator, identifier, etc.)
- `Manifest` (`package/manifest.py`): List of all resources in the EPUB
- `Spine` (`package/spine.py`): Reading order of content documents

### Navigation (epub_utils/navigation/)
- `Navigation` (base class): Abstract navigation interface
- `NCXNavigation` (`ncx/`): EPUB 2.0 navigation control file (toc.ncx)
- `EPUBNavDocNavigation` (`nav/`): EPUB 3.0 navigation document (nav.xhtml)

### Content (epub_utils/content/)
- `XHTMLContent`: Represents XHTML content documents with output methods (`to_xml()`, `to_str()`, `to_plain()`)

### Output Formatting
- All document classes have `to_str()` (raw XML), `to_xml()` (syntax highlighted), and some have `to_kv()` (key-value pairs)
- `XMLPrinter` (`printers.py`): Handles XML formatting and syntax highlighting via Pygments

### Exceptions (epub_utils/exceptions.py)
- `EPUBError`: Base exception with structured error messages and suggestions
- `ParseError`, `InvalidEPUBError`, `UnsupportedFormatError`, `FileNotFoundError`, `ValidationError`

## Testing

- Tests are in `tests/` directory
- Test fixtures use EPUB files in `tests/assets/`
- `conftest.py` provides the `doc_path` fixture pointing to test EPUB

## Dependencies

- `click`: CLI framework
- `lxml`: XML parsing (falls back to stdlib xml.etree if unavailable)
- `pygments`: Syntax highlighting
- `packaging`: Version parsing

## Installation for Development

This project uses **two parallel dependency management systems** (a common pattern in older Python projects):

### Two Systems Explained

| System | File | Purpose |
|--------|------|---------|
| setuptools | `setup.py` | Package metadata for pip/PyPI, flexible version specs |
| requirements | `requirements/*.txt` | Development dependencies with pinned versions |

### Quick Setup (Recommended)

```bash
# Step 1: Install package in editable mode (reads setup.py)
pip install -e .

# Step 2: Install all development dependencies (reads requirements.txt)
pip install -r requirements.txt
```

### What Each Command Installs

**`pip install -e .`** (from `setup.py`):
- Core dependencies: click, lxml, packaging, pygments, PyYAML
- Registers `epub-utils` CLI command

**`pip install -r requirements.txt`** (aggregates all requirements files):
- `requirements/requirements.txt` - Core dependencies (pinned versions)
- `requirements/requirements-testing.txt` - pytest, coverage
- `requirements/requirements-linting.txt` - ruff
- `requirements/requirements-docs.txt` - sphinx, furo

### Alternative: Using extras

```bash
# Install with specific extras defined in setup.py
pip install -e ".[test]"       # Core + pytest
pip install -e ".[docs]"       # Core + sphinx
pip install -e ".[test,docs]"  # Core + pytest + sphinx
```

### Why Two Systems?

- `setup.py` uses flexible versions (`click`) for end-user compatibility
- `requirements.txt` uses pinned versions (`click==8.1.8`) for reproducible dev environments
- Modern projects typically use `pyproject.toml` to unify both approaches
