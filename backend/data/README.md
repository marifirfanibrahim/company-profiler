# backend / data

storage and retrieval layer.

## responsibilities

- persist profiles to sqlite
- manage chromadb storage
- provide source retrievers
- run periodic seeding

## files

- `database.py`  
  sqlite manager for stored profiles  
  supports delete and list

- `document_store.py`  
  chromadb based vector store wrapped by haystack  
  used for caching and reusing past documents

## folders

- `sources/`  
  retrievers for external data sources  
  rss feeds  
  commoncrawl archive  
  official site scrapers  
  bursa selenium retriever

- `seeder/`  
  periodic seeding of chromadb  
  fetches and indexes relevant documents  

- `stores/`  
  runtime data folder  
  sqlite db, chroma folder, seed lists  
  some runtime-only files are ignored by git

## seeding commands

run from project root:

- seed chromadb
  ```bash
  python -m backend.data.seeder.seed_chromadb
  ```

- update seed entity list
  ```bash
  python -m backend.data.seeder.update_seed_entities development
  ```

## data paths
paths are centralized in:

backend/configuration/paths.py
main store files:
- sqlite profiles db: backend/data/stores/sqlite3.db
- chroma store folder: backend/data/stores/chroma_db/
- seed entities: backend/data/stores/seed_entities.json
- seed urls cache: backend/data/stores/seed_urls.json
- seed candidates: backend/data/stores/seed_entity_candidates.json

runtime-only state (ignored by git):
- selenium profile: backend/data/stores/selenium_profile/
- bursa backfill cursor: backend/data/stores/bursa_backfill.json