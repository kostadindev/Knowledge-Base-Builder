"""Verify the package works when optional (extras) dependencies are absent.

These deps are moved out of the core install in setup.py, so importing the
package and running the default path must not require them. The check runs in a
subprocess with an import blocker, because the deps are already imported in the
main test process.
"""

import subprocess
import sys
import textwrap


# Optional dependencies that live in setup.py extras, not the core install.
_BLOCKED = [
    "pandas",
    "ezodf",
    "openpyxl",
    "langchain_openai",
    "langchain_anthropic",
    "arxiv",
    "feedparser",
    "youtube_transcript_api",
    "pptx",
    "markitdown",
]


def _run(body: str) -> subprocess.CompletedProcess:
    script = textwrap.dedent(
        f"""
        import sys, importlib.abc
        BLOCKED = set({_BLOCKED!r})

        class _Blocker(importlib.abc.MetaPathFinder):
            def find_spec(self, name, path=None, target=None):
                if name.split(".")[0] in BLOCKED:
                    raise ImportError("blocked-for-test:" + name)
                return None

        sys.meta_path.insert(0, _Blocker())
        """
    ) + textwrap.dedent(body)
    return subprocess.run([sys.executable, "-c", script], capture_output=True, text=True)


def test_import_without_optional_deps():
    r = _run("import knowledge_base_builder\nprint('OK')")
    assert r.returncode == 0, r.stderr
    assert "OK" in r.stdout


def test_default_raw_build_without_optional_deps(tmp_path):
    src = tmp_path / "a.txt"
    src.write_text("slim install content", encoding="utf-8")
    out = tmp_path / "kb.md"
    r = _run(
        f"""
        import knowledge_base_builder as kbb
        kbb.build({str(src)!r}, out={str(out)!r})
        assert "slim install content" in open({str(out)!r}, encoding="utf-8").read()
        print("OK")
        """
    )
    assert r.returncode == 0, r.stderr
    assert "OK" in r.stdout


def test_spreadsheet_without_pandas_raises_actionable_error():
    r = _run(
        """
        from knowledge_base_builder import SpreadsheetProcessor
        try:
            SpreadsheetProcessor.extract_text("x.csv")
        except ImportError as e:
            assert "spreadsheets" in str(e), str(e)
            print("OK")
        else:
            raise SystemExit("expected ImportError")
        """
    )
    assert r.returncode == 0, r.stderr
    assert "OK" in r.stdout


def test_openai_provider_without_dep_raises_actionable_error():
    r = _run(
        """
        from knowledge_base_builder import KBBuilder
        try:
            KBBuilder({"OPENAI_API_KEY": "x"})
        except ImportError as e:
            assert "openai" in str(e).lower(), str(e)
            print("OK")
        else:
            raise SystemExit("expected ImportError")
        """
    )
    assert r.returncode == 0, r.stderr
    assert "OK" in r.stdout
