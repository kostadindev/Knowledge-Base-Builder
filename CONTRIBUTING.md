# Contributing to Knowledge Base Builder

Thank you for your interest in contributing! This document explains how to get started.

## Quick Start

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR-USERNAME/knowledge-base-builder.git`
3. Install in development mode: `pip install -e . && pip install -r test-requirements.txt`
4. Create a branch: `git checkout -b feature/your-feature`
5. Make your changes and add tests
6. Run the test suite: `pytest --cov=knowledge_base_builder`
7. Push and open a Pull Request

## Development Setup

```bash
git clone https://github.com/YOUR-USERNAME/knowledge-base-builder.git
cd knowledge-base-builder
pip install -e .
pip install -r test-requirements.txt
```

To run the package itself, you'll also need an LLM API key. Copy `.env.example` to `.env` and add your key.

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=knowledge_base_builder --cov-report=term-missing

# Run a specific test file
pytest knowledge_base_builder/tests/test_comprehensive.py
```

Tests are located in `knowledge_base_builder/tests/`. The CI pipeline runs tests on Python 3.9, 3.10, and 3.11. All PRs must pass the test suite with at least 70% coverage.

## Code Style

- Follow PEP 8
- Use `logging` instead of `print()` in all source modules (see existing code for patterns)
- Add docstrings for new public functions and classes
- Keep functions focused — one function, one responsibility
- Use type hints for function signatures

## Adding a New Source Type

To add support for a new file format:

1. Create a new processor in `knowledge_base_builder/` that extends `BaseProcessor`
2. Implement `download()` and `extract_text()` methods
3. Register the file extension in `kb_builder.py` `process_files_async()`
4. Add tests in `knowledge_base_builder/tests/`
5. Update the supported sources table in `README.md`

## Adding a New LLM Provider

1. Create a new client in `knowledge_base_builder/` that extends `LLMClient`
2. Implement `run_async()` with retry and exponential backoff
3. Add the provider selection logic in `KBBuilder.__init__()` in `kb_builder.py`
4. Add CLI arguments in `cli.py`
5. Add tests and update `README.md`

## Pull Request Process

1. Ensure all tests pass and coverage doesn't drop
2. Update documentation if your change affects the public API
3. Use the PR template (auto-populated when you create a PR)
4. A maintainer will review and provide feedback

## Bug Reports

Found a bug? [Open an issue](https://github.com/kostadindev/knowledge-base-builder/issues/new?template=bug_report.md) with:

- Steps to reproduce
- Expected vs. actual behavior
- Python version and OS
- Full error traceback

## Feature Requests

Have an idea? [Open an issue](https://github.com/kostadindev/knowledge-base-builder/issues/new?template=feature_request.md) describing the feature and its use case.

## Questions

Open an issue with your question. We're happy to help.
