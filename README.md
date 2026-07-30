# Knowledge Base Builder

<p align="center">
  <img src="https://kostadindev.github.io/images/kbb.svg" alt="Knowledge Base Builder" width="100%">
</p>

<p align="center">
  <a href="https://pypi.org/project/knowledge-base-builder/"><img src="https://img.shields.io/pypi/v/knowledge-base-builder" alt="PyPI"></a>
  <a href="https://github.com/kostadindev/knowledge-base-builder/actions/workflows/tests.yml"><img src="https://github.com/kostadindev/knowledge-base-builder/actions/workflows/tests.yml/badge.svg" alt="Tests"></a>
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT"></a>
</p>

<p align="center"><b>Turn any source into one structured Markdown knowledge base.</b></p>

Point it at web pages, PDFs, GitHub repos, YouTube videos, arXiv papers, RSS feeds,
notebooks, and slides — it extracts everything and consolidates it into a single,
LLM-structured document. Built for RAG, `/llms.txt`, vector-DB ingestion, and chatbots.

## Install

```bash
pip install knowledge-base-builder
```

## Quickstart

```python
import knowledge_base_builder as kbb

kbb.build("https://arxiv.org/abs/2301.12345", "octocat/Hello-World", "notes.pdf", out="kb.md")
```

Pass any mix of URLs, local paths, and `user/repo` shorthand — each is auto-routed to the
right extractor. Keys are read from the environment (`GOOGLE_API_KEY` / `OPENAI_API_KEY` /
`ANTHROPIC_API_KEY`).

**No key?** It still works — `build()` falls back to raw extraction so you always get a result:

```python
kbb.build("https://example.com", out="kb.md")   # zero configuration
```

## 📖 Documentation

**Full docs, guides, and API reference: [kostadindev.github.io/knowledge-base-builder](https://kostadindev.github.io/knowledge-base-builder)**

- [Installation](https://kostadindev.github.io/knowledge-base-builder/getting-started/installation/) — core + optional extras
- [Quickstart](https://kostadindev.github.io/knowledge-base-builder/getting-started/quickstart/) — one-liner, raw mode, full control, CLI
- [Sources](https://kostadindev.github.io/knowledge-base-builder/guides/sources/) · [Output Formats](https://kostadindev.github.io/knowledge-base-builder/guides/output-formats/) · [Generate `/llms.txt`](https://kostadindev.github.io/knowledge-base-builder/guides/llms-txt/)
- [API Reference](https://kostadindev.github.io/knowledge-base-builder/api/build/)

## Supported sources

| Source | Formats / detection |
|--------|---------------------|
| Documents | PDF, DOCX, TXT, MD, RTF |
| Spreadsheets | CSV, TSV, XLSX, ODS |
| Web content | HTML, XML, JSON, YAML/YML |
| Websites | any URL, or a whole `sitemap.xml` |
| GitHub | `user/repo` shorthand or GitHub URLs |
| YouTube | `youtube.com` / `youtu.be` URLs — transcripts |
| arXiv | `arxiv.org` URLs or bare IDs like `2301.12345` |
| RSS / Atom | feed URLs |
| Jupyter | `.ipynb` files |
| PowerPoint | `.pptx` files |

The core install is lean; heavier sources are opt-in extras
(`pip install "knowledge-base-builder[all]"`). See the
[installation guide](https://kostadindev.github.io/knowledge-base-builder/getting-started/installation/).

## Output formats

```python
kbb.build("https://mysite.com", out="llms.txt", output_format="llms_txt")   # /llms.txt spec
kbb.build("docs/",              out="chunks.json", output_format="chunks")   # vector-DB JSON
kbb.build("https://mysite.com", out="raw.md",   output_format="raw")         # no LLM / no key
```

## CLI

```bash
knowledge-base-builder -f https://example.com/resume.pdf -g username/repo -o kb.md
```

## Citing

If you use this package in your research, please cite:

```bibtex
@article{devedzhiev2026kbb,
  title = {Knowledge Base Builder: A Python Package for Multi-Source Knowledge Base Construction with Large Language Models},
  author = {Devedzhiev, Kostadin},
  journal = {Journal of Open Source Software},
  year = {2026}
}
```

## Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) and the
[Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md).

- **Bugs**: [open an issue](https://github.com/kostadindev/knowledge-base-builder/issues/new?template=bug_report.md)
- **Features**: [open an issue](https://github.com/kostadindev/knowledge-base-builder/issues/new?template=feature_request.md)

## License

MIT License. See [LICENSE](LICENSE) for details.
