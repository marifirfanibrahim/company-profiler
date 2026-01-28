# BZINT3
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
bzint3
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
1.  **Python**: Version 3.10 (it may not work in higher versions). Can find it here: [python.org](https://www.python.org/downloads/release/python-3100/).
2.  **Ollama**: Download it from [ollama.com](https://ollama.com).
3. (OPTIONAL) **Tesseract-OCR**: Download it from [tesseract-ocr.com](https://tesseract-ocr.com/#download).

### Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/marifirfanibrahim/bzint3.git
    cd bzint3
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

### How to Run

1. **Run Ollama from terminal** <-- **IMPORTANT!**
    ```powershell
    ollama serve
    ```

2.  **Run application**
    ```bash
    python run.py
    ```

3.  **Access web interface**:
    **`http://localhost:5000`** 
