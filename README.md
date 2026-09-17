# Company Profiler
Business intelligence reports based on open source data. This project is a Retrieval-Augmented Generation (RAG) system. It is designed to obtain information from the queried company, the snapshot or business updates, customer profiles, corporate guarantor profiles, and the high-risk entities and individuals.

## Table of Contents
1. [Architecture](#1-architecture)
2. [File Structure Map](#2-file-structure-map)
3. [Data Stores](#3-data-stores)
4. [Setup and Installation](#4-setup-and-installation)


## 1. Architecture

### High-Level Architecture
![high-level-architecture](<doc/high-level-architecture.png>)


### Layers
![layers](<doc/layers.png>)

There are 2 main layer, with 5 sub-layers:
- Data collection layer, with:
-- input layer (either from user or entity list)
-- database layer
-- online layer (web scraping)
-- agent layer (component library)

- Data retreival layer, with:
-- output layer (search results)
-- agent layer (component library)


### Output Flow
![output-flow](<doc/output-flow.png>)

Detailed version to show how the output is produced.


### Growth Loop
![growth-loop](<doc/growth-loop.png>)

The entity list is grown by itself and by the entities from the results.


### Data Flow
![data-flow](<doc/data-flow.png>)

Shows how the data is obtained, processed, and perpetuated.


### Seed Flow
![seed-flow](<doc/seed-flow.png>)

Shows how the entities is involved in data collection. Entities used in seeding are both with and without suffixes.


## 2. File Structure Map

### High-Level Map

```
company_profiler
├── README.md
├── backend/
├── frontend/
├── requirements.txt
└── run.py
```


### Frontend

```
frontend
├── README.md
├── init.py
│ 
├── flaskr
│ ├── README.md
│ ├── init.py
│ ├── components.py
│ │ 
│ ├── routes
│ │ ├── README.md
│ │ ├── init.py
│ │ ├── main.py
│ │ └── search.py
│ │ 
│ ├── static
│ │ ├── README.md
│ │ ├── css
│ │ │ ├── README.md
│ │ │ ├── core.css
│ │ │ ├── dark-mode.css
│ │ │ ├── pages.css
│ │ │ └── style.css
│ │ │
│ │ └── js
│ │   ├── README.md
│ │   ├── config.js
│ │   ├── search.js
│ │   ├── ui_config.js
│ │   └── utils.js
│ │
│ └── templates
│   ├── README.md
│   └── index.html
│ 
└── instance
└── README.md
```


### Backend

```
backend
├── init.py
├── components
│ ├── init.py
│ ├── content_extractor.py
│ └── document_retriever.py
│ 
├── configuration
│ ├── init.py
│ ├── README.md
│ ├── bursa_company_codes.json
│ ├── bursa_config.py
│ ├── case.py
│ ├── commoncrawl_indices.json
│ ├── config.py
│ ├── labels.py
│ ├── models.py
│ ├── paths.py
│ ├── profile.py
│ ├── prompts.py
│ ├── seeding.py
│ ├── sources.py
│ ├── sql.py
│ └── words.py
│ 
├── data
│ ├── README.md
│ ├── database.py
│ ├── document_store.py
│ ├── seeder
│ │ ├── init.py
│ │ ├── scheduler.py
│ │ ├── seed_chromadb.py
│ │ └── update_seed_entities.py
│ │
│ ├── sources
│ │ ├── init.py
│ │ ├── README.md
│ │ ├── bursa.py
│ │ ├── commoncrawl.py
│ │ ├── factory.py
│ │ ├── marc_ratings.py
│ │ ├── official_cases.py
│ │ ├── ram_ratings.py
│ │ └── rss.py
│ │
│ └── stores
│   ├── chroma_db
│   ├── sqlite3.db
│   ├── seed_entities.json
│   ├── seed_entity_candidates.json
│   └── seed_urls.json
│ 
├── helpers
│ ├── fetch
│ │ ├── init.py
│ │ ├── bursa_helpers.py
│ │ ├── httpx_helpers.py
│ │ ├── query_helpers.py
│ │ ├── selenium_helpers.py
│ │ └── source_helpers.py
│ │
│ ├── logic
│ │ ├── init.py
│ │ ├── fact_check_helpers.py
│ │ ├── helper.py
│ │ ├── pipeline_helpers.py
│ │ ├── ranking_helpers.py
│ │ └── seed_helpers.py
│ │
│ ├── parse
│ │ ├── init.py
│ │ ├── date_helpers.py
│ │ ├── ocr_helpers.py
│ │ ├── pdf_utils.py
│ │ └── text_helpers.py
│ │
│ └── persist
│ ├── init.py
│ ├── json_utils.py
│ ├── model_registry_helpers.py
│ └── store_helpers.py
│ 
├── models
│ ├── init.py
│ ├── README.md
│ ├── entity_extractor.py
│ ├── fact_checker.py
│ ├── generator.py
│ ├── profile_extractor.py
│ ├── relationship_extractor.py
│ ├── reranker.py
│ └── snapshot_extractor.py
│ 
└── pipeline
  ├── init.py
  ├── core.py
  ├── output.py
  ├── retrieval.py
  └── summarization.py
```


## 3. Data Stores

Generated runtime files are stored under:
- `backend/data/stores/`

Key store files:
- sqlite profiles db: `backend/data/stores/sqlite3.db`
- chromadb folder: `backend/data/stores/chroma_db/`
- seed urls cache: `backend/data/stores/seed_urls.json`
- seed entities list: `backend/data/stores/seed_entities.json`
- seed entity candidates list: `backend/data/stores/seed_entity_candidates.json`


## 4. Setup and Installation

### Prerequisites

Before you begin, ensure you have the following installed on your system:
1.  **Python 3.10.2 or newer 3.10.x** (tested on 3.10.20; 3.10.11 resolves to identical pins): required. 3.10.0 and 3.10.1 need extra packages (`importlib-metadata`, `zipp`) that the lock does not contain, and 3.11+ is not supported because of the `gliner`, `glirel` and `torch` pins. Install it with `uv` (`uv python install 3.10`, shown under Installation), or with the [python.org 3.10.11 Windows installer](https://www.python.org/downloads/release/python-31011/).
2.  **uv** (recommended): follow the [installation guide](https://docs.astral.sh/uv/getting-started/installation/).
3.  **Ollama**: download it from [ollama.com](https://ollama.com), then pull the default model:
    ```powershell
    ollama pull llama3:8b
    ```
4.  **Google Chrome**: used by Selenium for Bursa Malaysia scraping.
5. (OPTIONAL) **Tesseract-OCR**: install it by following the [official Tesseract installation docs](https://tesseract-ocr.github.io/tessdoc/Installation.html) (on Windows, use the UB Mannheim installer linked from that page). OCR is off by default: `OCR_ENABLED` is hard-coded to `False` in `backend/configuration/config.py` and is not read from `.env`, so OCR never runs unless that constant is changed to `True`. When OCR is enabled, the app uses the path in `OCR_TESSERACT_CMD` (set in `.env`) if that file exists; if the variable is unset or the path is invalid, it looks for `tesseract` on PATH instead. If neither is found, OCR returns no text and extraction continues without it.

### Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/marifirfanibrahim/company-profiler.git
    cd company-profiler
    ```

2.  **Create the virtual environment and install the locked dependencies:**

    **Option A: uv (recommended)**
    ```bash
    uv python install 3.10
    uv venv --python 3.10
    uv pip sync requirements.lock
    ```
    These `uv` commands are the same in PowerShell and Git Bash, and none of them needs the venv to be activated. `uv venv` does not install pip into the environment, so use `uv pip` for later package commands, or create the venv with `uv venv --seed --python 3.10` if you need `pip` itself.

    **Option B: pip**

    PowerShell:
    ```powershell
    python -m venv .venv
    Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
    .venv\Scripts\Activate.ps1
    pip install -r requirements.lock
    ```
    Git Bash:
    ```bash
    python -m venv .venv
    source .venv/Scripts/activate
    pip install -r requirements.lock
    ```
    (run `python -m venv` with a Python 3.10.2 or newer 3.10.x interpreter)

    > - On a default Windows client, PowerShell's execution policy blocks `Activate.ps1` with "running scripts is disabled on this system". `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force` lifts that for the current PowerShell window only and leaves the machine and user policy unchanged; run it again in each new window before activating.

    > - `requirements.lock` holds the exact tested versions and is the supported install path. `requirements.txt` holds the version ranges and upper bounds (with each bound's reason in a comment) and is only the input for regenerating the lock.
    > - The lock targets Windows x64 (`win_amd64`) with CPython 3.10.2 or newer 3.10.x (tested on 3.10.20); see the Linux Note below.
    > - `seqeval` 1.2.2 has no wheel on PyPI, so a first install on a machine with a cold package cache builds it from source and needs network access for that build.

3.  **Create the `.env` file:**

    PowerShell:
    ```powershell
    Copy-Item .env.example .env
    ```
    Git Bash:
    ```bash
    cp .env.example .env
    ```
    Then set the following keys (see `.env.example` for placeholders):
    - `FLASK_ENV`: `development`, `production` or `testing`; when unset the app runs as `production`.
    - `OPENAI_API_KEY`: only needed for OpenAI models.
    - `ANTHROPIC_API_KEY`: only needed for Anthropic models.
    - `OCR_TESSERACT_CMD`: optional, full path to `tesseract.exe`; only used when `OCR_ENABLED` is `True` in `backend/configuration/config.py`, and `tesseract` on PATH is used when it is unset or invalid.
    - `FLASK_SECRET_KEY`: a long random string.
    - `HTTP_VERIFY_TLS`: optional, defaults to `true`.

    Keep `.env` out of version control.

### First Run: Model Downloads

The first `python run.py` downloads the Hugging Face models used by the pipeline into the Hugging Face cache (`%USERPROFILE%\.cache\huggingface` by default on Windows). It also downloads NLTK's `punkt_tab` tokenizer (about 4 MB, fetched automatically by haystack's sentence splitter) into NLTK's default data folder. Startup is slow until these finish — budget about 6.9 GB total and time proportional to your connection speed.

| Model | Used for | Size | Known-good commit |
|-------|----------|------|--------------------|
| BAAI/bge-reranker-v2-m3 | reranking | 2.3 GB | `953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e` |
| MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7 | fact checking (NLI) | 0.6 GB | `b5113eb38ab63efdd7f280f8c144ea8b13f978ce` |
| jackboyla/glirel-large-v0 | relationship extraction | 1.9 GB | `40a523e12a8432d6da364cf2a195a28755ff04d3` |
| microsoft/deberta-v3-large | backbone loaded by GLiREL (jackboyla/glirel-large-v0) | 0.9 GB | `64a8c8eab3e352a784c658aef62be1662607476f` |
| microsoft/mdeberta-v3-base | backbone loaded by GLiNER (urchade/gliner_multi) | 0.0 GB | `a0484667b22365f84929a935b5e50a51f71f159d` |
| sentence-transformers/all-MiniLM-L6-v2 | embeddings | 0.1 GB | `1110a243fdf4706b3f48f1d95db1a4f5529b4d41` |
| urchade/gliner_multi | entity extraction | 1.2 GB | `b5720abb5b8c575e626e54a7c1001761db8b08db` |

The commit IDs above were observed in the 2026-09-17 boot check and are documentation only; the app does not pin model revisions.

**IMPORTANT!** Before the first run, set `DISABLE_SAFETENSORS_CONVERSION=true` in your shell.

PowerShell:
```powershell
$env:DISABLE_SAFETENSORS_CONVERSION = "true"
```
Git Bash:
```bash
export DISABLE_SAFETENSORS_CONVERSION=true
```
Without it, `transformers` starts a background download of an extra ~874 MB safetensors copy of `microsoft/deberta-v3-large` that the app does not need, and that download competes with the real model downloads for bandwidth.

**Optional pre-download** of the largest model, the reranker (about 2.3 GB; an interrupted download resumes when re-run). With the venv active:

PowerShell:
```powershell
$env:DISABLE_SAFETENSORS_CONVERSION = "true"
hf download BAAI/bge-reranker-v2-m3
```
Git Bash:
```bash
export DISABLE_SAFETENSORS_CONVERSION=true
hf download BAAI/bge-reranker-v2-m3
```

**Moving the caches:** to keep models or NLTK data somewhere else, set `HF_HOME` and/or `NLTK_DATA` in the shell before `python run.py` — not in `.env`, because a value in `.env` is ignored when the variable is already set in the environment. Example (paths below are illustrative):

PowerShell:
```powershell
$env:HF_HOME = "D:\hf-cache"
$env:NLTK_DATA = "D:\nltk_data"
python run.py
```
Git Bash:
```bash
export HF_HOME=/d/hf-cache
export NLTK_DATA=/d/nltk_data
python run.py
```

### How to Run

1. **Run Ollama from terminal** <-- **IMPORTANT!**
    ```powershell
    ollama serve
    ```

2.  **Run application**

    PowerShell:
    ```powershell
    Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
    .venv\Scripts\Activate.ps1
    python run.py
    ```
    Git Bash:
    ```bash
    source .venv/Scripts/activate
    python run.py
    ```
    Or, in either shell and without activating the venv: `uv run python run.py`.

3.  **Access web interface**:
    **`http://localhost:5000`**

### Linux Note

`requirements.lock` is resolved for Windows x64 (`win_amd64`) and CPython 3.10.x (3.10.2 or newer) only. On Linux, PyPI's `torch` 2.14.0 is the CUDA 13 build (about 3 GB including the `nvidia-*` and `triton` packages). A Linux host needs its own lock; on a machine without a GPU, resolve `torch` from the PyTorch CPU index instead: `https://download.pytorch.org/whl/cpu`.

### Updating the Lock

Run these steps in Git Bash. `uv pip compile` writes only header lines 1-2 of `requirements.lock`; lines 3-5 (platform, freeze source and date, edit note) are notes that step 4 saves before compiling and puts back afterwards.

1. Edit the ranges in `requirements.txt`.
2. Install into `.venv` and confirm `python run.py` reaches profiles db, document store and pipeline `[OK]`.
3. Create a folder outside the repository and copy `requirements.txt` and `requirements.lock` into it. From the repository root, save that venv's freeze, minus any pip and wheel lines, into the folder as `boot-verified-freeze.txt`:
    ```bash
    uv pip freeze --python .venv/Scripts/python.exe | grep -vE '^(pip|wheel)==' > /path/to/folder/boot-verified-freeze.txt
    ```
4. In that folder, save lines 3-5, run the `uv pip compile` command recorded on line 2 of `requirements.lock`, then put lines 3-5 back:
    ```bash
    sed -n 3,5p requirements.lock > lock-notes.txt
    uv pip compile requirements.txt -c boot-verified-freeze.txt --python-version 3.10.20 --python-platform x86_64-pc-windows-msvc --annotation-style line -o requirements.lock
    { head -n 2 requirements.lock; cat lock-notes.txt; tail -n +3 requirements.lock; } > requirements.lock.new
    mv requirements.lock.new requirements.lock
    ```
    Update the freeze date on line 4 (and line 3 if the platform or Python version changed), then copy `requirements.lock` back into the repository.
5. Confirm `uv pip sync requirements.lock --dry-run` reports `Would make no changes`.
