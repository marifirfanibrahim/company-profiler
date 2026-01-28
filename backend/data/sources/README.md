# backend / data / sources

retrievers and utilities for external data sources.

## responsibilities

- fetch candidate urls and snippets
- return haystack `Document` rows
- keep per source limits and filters

## retrievers

- `rss.py`  
  rss feed retriever  
  supports news feeds and google news feeds  
  filters by query words

- `commoncrawl.py`  
  commoncrawl index search  
  fetches archived pages  
  extracts full content

- `official_cases.py`  
  official site scrapers  
  bnm, sc, sprm, pdrm, agc, judiciary

- `bursa.py`  
  bursa announcement retriever  
  uses selenium for blocked pages  
  requires `backend/configuration/bursa_company_codes.json`  
  stores runtime cursor in `backend/data/stores/bursa_backfill.json` (ignored by git)

- `ram_ratings.py`  
  ram ratings search + press release extraction  
  extracts rating announcements text

- `marc_ratings.py`  
  marc ratings search + article extraction  
  extracts rating announcements text

- `factory.py`  
  builds enabled retrievers  
  applies disabled source list

## source configuration

source settings and feeds are centralized in:
- `backend/configuration/sources.py`