import json
import os
import tempfile
import pytest
from knowledge_base_builder.jupyter_processor import JupyterProcessor


def _make_notebook(cells, kernel_language="python"):
    """Helper to create a minimal .ipynb notebook dict."""
    return {
        "metadata": {
            "kernelspec": {
                "language": kernel_language,
                "display_name": kernel_language.capitalize(),
            }
        },
        "nbformat": 4,
        "nbformat_minor": 5,
        "cells": cells,
    }


def _write_notebook(nb_dict, tmpdir):
    """Write notebook dict to a temp .ipynb file and return its path."""
    path = os.path.join(tmpdir, "test_notebook.ipynb")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(nb_dict, f)
    return path


class TestJupyterExtractText:
    def test_extract_markdown_cell(self):
        nb = _make_notebook([
            {"cell_type": "markdown", "source": ["# Title\n", "Some description"], "metadata": {}},
        ])
        with tempfile.TemporaryDirectory() as tmpdir:
            path = _write_notebook(nb, tmpdir)
            result = JupyterProcessor.extract_text(path)
        assert "# Title" in result
        assert "Some description" in result

    def test_extract_code_cell(self):
        nb = _make_notebook([
            {"cell_type": "code", "source": ["print('hello')"], "metadata": {}, "outputs": []},
        ])
        with tempfile.TemporaryDirectory() as tmpdir:
            path = _write_notebook(nb, tmpdir)
            result = JupyterProcessor.extract_text(path)
        assert "```python" in result
        assert "print('hello')" in result

    def test_extract_mixed_cells(self):
        nb = _make_notebook([
            {"cell_type": "markdown", "source": ["# Intro"], "metadata": {}},
            {"cell_type": "code", "source": ["x = 1"], "metadata": {}, "outputs": []},
            {"cell_type": "raw", "source": ["raw text here"], "metadata": {}},
        ])
        with tempfile.TemporaryDirectory() as tmpdir:
            path = _write_notebook(nb, tmpdir)
            result = JupyterProcessor.extract_text(path)
        assert "# Intro" in result
        assert "x = 1" in result
        assert "raw text here" in result

    def test_extract_with_outputs(self):
        nb = _make_notebook([
            {
                "cell_type": "code",
                "source": ["print('hello')"],
                "metadata": {},
                "outputs": [
                    {"output_type": "stream", "name": "stdout", "text": ["hello\n"]},
                    {
                        "output_type": "execute_result",
                        "data": {"text/plain": ["42"]},
                        "metadata": {},
                        "execution_count": 1,
                    },
                ],
            }
        ])
        with tempfile.TemporaryDirectory() as tmpdir:
            path = _write_notebook(nb, tmpdir)
            result = JupyterProcessor.extract_text(path)
        assert "**Output:**" in result
        assert "hello" in result
        assert "42" in result

    def test_empty_notebook(self):
        nb = _make_notebook([])
        with tempfile.TemporaryDirectory() as tmpdir:
            path = _write_notebook(nb, tmpdir)
            result = JupyterProcessor.extract_text(path)
        assert result == ""

    def test_download_local_file(self):
        nb = _make_notebook([
            {"cell_type": "markdown", "source": ["# Test"], "metadata": {}},
        ])
        with tempfile.TemporaryDirectory() as tmpdir:
            path = _write_notebook(nb, tmpdir)
            file_url = f"file://{path}"
            downloaded = JupyterProcessor.download(file_url)
            assert downloaded == path
            assert os.path.exists(downloaded)
