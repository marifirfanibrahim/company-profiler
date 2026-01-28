# frontend / flaskr / routes

api and page routes.

## files

- `main.py`  
  index html page  
  health endpoint  
  model config endpoints  
  custom model endpoints  
  profile list and delete endpoints

- `search.py`  
  `/search` post endpoint  
  calls backend pipeline  
  stores results in sqlite  
  optionally indexes documents in chromadb

- `__init__.py`  
  exports blueprints for registration