# backend / configuration

configuration modules and static json files.

## files

- `config.py`  
  main application settings  
  model ids and thresholds  
  pipeline and storage limits

- `models.py`  
  model registry  
  default models and custom models  
  reads `custom_models.json`

- `paths.py`  
  all file and folder paths  
  used across backend and frontend

- `sources.py`  
  rss feed urls  
  commoncrawl indices loader  
  user agents and domain lists

- `bursa_config.py`  
  bursa selenium settings  
  listing and detail url paths  
  extraction limits

- `seeding.py`  
  seeding schedule and limits  
  seed expansion and promotion rules

## json files

- `commoncrawl_indices.json`  
  list of crawl ids  
  update when new crawls appear

- `bursa_company_codes.json`  
  mapping of company names to bursa code  
  required for bursa listing

- `custom_models.json`  
  optional custom model definitions  
  ignored by git

## runtime state files

these paths are defined in `paths.py` but are runtime state and ignored by git:

- `backend/data/stores/bursa_backfill.json`  
  bursa backfill cursor state

- `backend/data/stores/selenium_profile/`  
  local selenium browser profile