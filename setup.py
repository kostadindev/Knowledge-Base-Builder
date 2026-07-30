import re
import pathlib

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()


def _read_version() -> str:
    """Single-source the version from the package __init__ (no import needed)."""
    init = pathlib.Path(__file__).parent / "knowledge_base_builder" / "__init__.py"
    text = init.read_text(encoding="utf-8")
    match = re.search(r'^__version__\s*=\s*["\']([^"\']+)["\']', text, re.MULTILINE)
    if not match:
        raise RuntimeError("Unable to find __version__ in knowledge_base_builder/__init__.py")
    return match.group(1)

# Core dependencies: enough to import the package, run the default Gemini
# provider, and process web pages, PDFs, documents (docx/txt/md/rtf), and web
# content (html/xml/json/yaml). Heavy/rarely-needed sources live in extras.
CORE_REQUIRES = [
    "langchain>=0.1.0",
    "langchain-google-genai>=0.0.5",
    "langchain-community>=0.0.13",
    "beautifulsoup4>=4.12.2",
    "requests>=2.31.0",
    "python-dotenv>=1.0.0",
    "lxml>=4.9.3",
    "pypdf>=3.17.0",
    "python-docx>=0.8.11",  # .docx
    "markdown>=3.4.3",      # .md
    "mistune>=2.0.5",       # alternative Markdown parser
    "striprtf>=0.0.22",     # .rtf
    "pyyaml>=6.0",          # .yaml/.yml
]

EXTRAS = {
    "spreadsheets": ["pandas>=2.0.0", "openpyxl>=3.1.2", "ezodf>=0.3.2"],  # csv/tsv/xlsx/ods
    "youtube": ["youtube-transcript-api>=0.6.0"],
    "rss": ["feedparser>=6.0.0"],
    "pptx": ["python-pptx>=0.6.21"],
    "arxiv": ["arxiv>=2.0.0"],
    "openai": ["langchain-openai>=0.1.0"],
    "anthropic": ["langchain-anthropic>=0.1.0"],
    "markitdown": ["markitdown"],
}
# ``[all]`` installs every optional feature.
EXTRAS["all"] = sorted({dep for deps in EXTRAS.values() for dep in deps})

setup(
    name="knowledge-base-builder",
    version=_read_version(),
    author="Kostadin Devedzhiev",
    author_email="kostadin.g.devedzhiev@gmail.com", 
    description="🚀 Builds a structured markdown knowledge base from external sources such as websites, documents, and GitHub repos with large language models. Ideal for RAG, SEO-friendly LLM contexts (/llms.txt), and chatbots.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/kostadindev/knowledge-base-builder",
    project_urls={
        "Homepage": "https://github.com/kostadindev/knowledge-base-builder",
        "Documentation": "https://github.com/kostadindev/knowledge-base-builder#readme",
    },
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Documentation",
        "Topic :: Text Processing :: Markup",
    ],
    python_requires=">=3.8",
    install_requires=CORE_REQUIRES,
    extras_require=EXTRAS,
    entry_points={
        "console_scripts": [
            "knowledge-base-builder=knowledge_base_builder.cli:main",
        ],
    },
) 