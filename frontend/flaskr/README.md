# frontend

web user interface.

## structure

- `flaskr/`  
  flask application package  
  templates, static assets, blueprints, component wiring

- `instance/`  
  flask instance folder placeholder  
  can hold per deployment configuration files

## responsibilities

- render search page  
- call backend api endpoints for search and config  
- manage client side state and interactions  
- show sources and export files

## endpoints used

- `POST /search`  
- `GET /api/models`  
- `GET /api/custom-models`  
- `POST /api/custom-models`  
- `DELETE /api/custom-models/<model_id>`  
- `GET /api/profiles`  
- `GET /api/profiles/<profile_id>`  
- `DELETE /api/profiles/<profile_id>`