# Document Tools

A bilingual (English / French) Streamlit app that bundles a few `.docx` utilities backed by Azure AI Translator and a vendored image-shrinker. Oversized files are automatically shrunk to fit Azure's 10 MB synchronous-translation limit by re-encoding embedded images.

## Features

- **Translate** — upload a `.docx`, pick **English → French** or **French → English**, download the translated file. Files over 10 MB are auto-shrunk before translation.
- **Shrink** — upload a `.docx` and re-encode embedded images to a target size (default 10 MB).
- **Format** — upload a `.docx`, optionally shrink its images, then clean up formatting: manual font colours are reset to automatic, fragmented (disjointed) text runs are merged, smart-tag wrappers are unwrapped, and stray proofing marks and orphaned field runs are removed. A downloadable summary reports what changed.
- Full English / French UI via a toggle in the top nav.
- Library functions in `src/helpers.py` and `src/doc_shrinker.py` are also usable from notebooks / CLI scripts.

## Requirements

- **Python 3.13+**
- **[uv](https://docs.astral.sh/uv/)** for dependency management
- An **Azure Translator** resource (endpoint + key)
- *(Optional)* An **Azure OpenAI** or **Ollama** endpoint if you'll use the chat helpers in `src/helpers.py`

## Install

```bash
git clone <this repo>
cd Document-Tools
uv sync
```

Copy `.env.template` to `.env` and fill in your credentials:

```dotenv
# Translator
AZURE_TRANSLATOR_ENDPOINT=https://<your-resource>.cognitiveservices.azure.com/
AZURE_TRANSLATOR_API_KEY=<your-key>

# Proofreader 
AZURE_OPENAI_ENDPOINT=https://<your-resource>.openai.azure.com/openai/v1
AZURE_API_KEY=<your-key>

# Optional - chat helpers, substitute endpoints, etc
OLLAMA_ENDPOINT=http://localhost:11434/v1
OLLAMA_API_KEY=<any-string>
```

## Run the Streamlit app

```bash
uv run streamlit run streamlit_app.py
```

Open <http://localhost:8501> in a browser. Tabs across the top — **Translate**, **Proofread**, **Shrink**, **Format**, **Settings** — switch between tools, with a language toggle on the right.

## Run from Python / a notebook

```python
from pathlib import Path
from src.helpers import translate_document, translate_document_bytes

# File on disk — writes <stem>_translated.docx next to the input
translate_document(Path("input.docx"), input_language="fr")

# Bytes in / bytes out — useful for web apps and batch jobs
data = Path("input.docx").read_bytes()
translated = translate_document_bytes(data, source_language="en")
Path("output_translated.docx").write_bytes(translated)
```

To shrink a `.docx` independently of translation:

```python
from src.doc_shrinker import compress_docx_images
compress_docx_images("big.docx", target_bytes=10 * 1024 * 1024)
# writes big_compressed.docx
```

To clean up formatting (reset manual colours, merge disjointed runs):

```python
from src.doc_formatter import format_document
format_document("messy.docx")
# writes messy_formatted.docx
```

## Run in Docker

```bash
docker build -t document-tools .
docker run --rm -p 8501:8501 --env-file .env document-tools
```

The image does **not** bake in `.env` — credentials must be injected at runtime (`--env-file`, `-e`, or your orchestrator's secret mechanism).

## Project layout

```
Document-Tools/
├── streamlit_app.py            # Web UI entry point + page router
├── pages/
│   ├── translate.py            # Translate tab
│   ├── proofread.py            # Proofread tab
│   ├── shrink.py               # Shrink tab
│   ├── format.py               # Format tab
│   └── settings.py             # Settings tab
├── src/
│   ├── helpers.py              # Azure Translator + Azure OpenAI/Ollama chat helpers
│   ├── doc_formatter.py        # Resets manual colours + merges disjointed text runs
│   ├── doc_shrinker.py         # Image re-encoder (vendored from KevinCarr42/Doc-Shrinker)
│   ├── proofreader.py          # LLM proofreading pass over a translated .docx
│   ├── proofread_cli.py        # CLI entry point for the proofread subprocess
│   ├── shrink_cli.py           # CLI entry point for the shrink subprocess
│   ├── subprocess_helpers.py   # Runs shrink/proofread in child processes to reclaim memory
│   ├── tab_guard.py            # Clears stale page state + nav-confirmation guard
│   ├── i18n.py                 # EN/FR string table + widget-text overrides
│   ├── styles.py               # Global CSS + JS text replacements for Streamlit chrome
│   └── utils.py                # Small formatting helpers
├── tests/
│   ├── conftest.py             # Shared pytest fixtures (docx/image builders, fakes)
│   └── test_*.py               # Unit tests, one file per src/ module
├── .streamlit/config.toml      # Streamlit theme + server config
├── Dockerfile
├── pyproject.toml
└── .env.template
```

## Limits and caveats

- Azure's **SingleDocumentTranslationClient caps at 10 MB**. Files over 10 MB are auto-shrunk; if the result is *still* over 10 MB (mostly-text documents with no compressible images), translation is rejected. Async batch translation (up to 40 MB) is not yet implemented.
- v1 supports `.docx` only. PDF / PPTX / XLSX are on the Azure Translator capability list but aren't exposed here yet.
- Source language is user-selected. Auto-detection isn't wired up.

## Deploying to an internal server

The `Dockerfile` is the portable contract. Host-specific bits to add when the target is chosen:

- **Secrets injection** — k8s Secret, `docker --env-file`, Windows service env, etc.
- **TLS / reverse proxy** — Streamlit serves plain HTTP on `:8501`. Front it with nginx / IIS / your platform's ingress.
- **Subpath mounting** — pass `--server.baseUrlPath=/document-tools` (or similar) if not served from the root.

## Roadmap

- LLM proofreading pass over the translated document.
- Async batch translation client for files >10 MB after shrinking.
- Custom Translator `category` support for domain-tuned models.
- Auto-detect source language.
- Additional document formats (`.pdf`, `.pptx`, `.xlsx`).
