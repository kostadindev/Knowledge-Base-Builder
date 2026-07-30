"""One-line convenience API for Knowledge Base Builder.

Example
-------
>>> import knowledge_base_builder as kbb
>>> kbb.build("https://arxiv.org/abs/2301.12345", "user/repo", "notes.pdf", out="kb.md")
'kb.md'

The heavy lifting still lives in :class:`~knowledge_base_builder.kb_builder.KBBuilder`;
this module only removes ceremony: it reads API keys from the environment, routes each
positional source to the right ``sources`` bucket, and falls back to key-free ``raw``
extraction when no LLM key is available.
"""

import os
import re
from typing import Any, Dict, List, Optional

from knowledge_base_builder.kb_builder import KBBuilder

__all__ = ["build", "config_from_env", "classify_sources"]

# username/repo shorthand. A GitHub username is alphanumeric + hyphens only (no
# dots, no underscores), which distinguishes it from a bare host like
# ``example.com/page``; the repo segment may contain dots/underscores.
_GITHUB_SHORTHAND = re.compile(r"^[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9_.-]+$")
_GITHUB_URL = re.compile(r"^https?://(?:www\.)?github\.com/[^/]+/[^/]+/?$", re.IGNORECASE)


def config_from_env() -> Dict[str, Any]:
    """Build a config dict from the standard environment variables."""
    config: Dict[str, Any] = {}
    for key in (
        "GOOGLE_API_KEY",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "GITHUB_API_KEY",
    ):
        value = os.environ.get(key)
        if value:
            config[key] = value
    return config


def _is_github(source: str) -> bool:
    if _GITHUB_URL.match(source):
        return True
    if source.startswith(("http://", "https://", "file://")):
        return False
    # Bare ``user/repo`` — but not a local path that actually exists on disk.
    if _GITHUB_SHORTHAND.match(source) and not os.path.exists(source):
        # Reject obvious file paths (segment with a known-looking extension is
        # still allowed through to files; github repos rarely end in a dotted ext).
        return True
    return False


def _is_sitemap(source: str) -> bool:
    return "sitemap" in source.lower() and source.lower().endswith(".xml")


def classify_sources(sources: List[str]) -> Dict[str, Any]:
    """Route a flat list of source strings into a ``KBBuilder`` sources dict.

    - GitHub ``user/repo`` shorthand or ``github.com`` URLs -> ``github_repositories``
    - ``*sitemap*.xml`` URLs -> ``sitemap_url``
    - everything else -> ``files`` (KBBuilder auto-detects the concrete type)
    """
    files: List[str] = []
    github: List[str] = []
    sitemap: Optional[str] = None

    for source in sources:
        source = source.strip()
        if not source:
            continue
        if _is_github(source):
            github.append(source)
        elif _is_sitemap(source):
            sitemap = source
        else:
            files.append(source)

    result: Dict[str, Any] = {"files": files}
    if github:
        result["github_repositories"] = github
    if sitemap:
        result["sitemap_url"] = sitemap
    return result


def build(
    *sources: str,
    out: str = "knowledge_base.md",
    config: Optional[Dict[str, Any]] = None,
    **build_kwargs: Any,
) -> Any:
    """Build a knowledge base from one or more sources in a single call.

    Args:
        *sources: Any mix of URLs, local file paths, ``user/repo`` GitHub
            shorthand, GitHub URLs, or a ``*sitemap*.xml`` URL.
        out: Output file path (default ``knowledge_base.md``).
        config: Optional explicit config dict. When omitted, keys are read from
            the environment (``GOOGLE_API_KEY`` / ``OPENAI_API_KEY`` /
            ``ANTHROPIC_API_KEY`` / ``GITHUB_API_KEY``).
        **build_kwargs: Forwarded to :meth:`KBBuilder.build` (e.g.
            ``output_format``, ``incremental``, ``validate``).

    Returns:
        The output file path (or a dict when ``dry_run=True``).

    When no LLM key is found, the build runs key-free in ``raw`` mode so a first
    result is always produced; pass an explicit ``output_format`` to override.
    """
    if not sources:
        raise ValueError(
            "build() requires at least one source. Example: "
            "kbb.build('https://example.com', out='kb.md')."
        )
    non_str = next((s for s in sources if not isinstance(s, str)), None)
    if non_str is not None:
        hint = (
            " If you have a list, unpack it: kbb.build(*my_sources, out=...)."
            if isinstance(non_str, (list, tuple, set))
            else ""
        )
        raise TypeError(
            "Each source must be a string (URL, file path, or 'user/repo'). Got "
            f"{type(non_str).__name__}: {non_str!r}.{hint}"
        )

    cfg = config if config is not None else config_from_env()
    has_llm_key = any(
        cfg.get(k) for k in ("GOOGLE_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY")
    )

    builder = KBBuilder(cfg, allow_no_llm=not has_llm_key)
    source_dict = classify_sources(list(sources))
    return builder.build(sources=source_dict, output_file=out, **build_kwargs)
