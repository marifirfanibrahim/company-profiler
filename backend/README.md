# backend

core application logic.

## structure

- `pipeline.py`  
  orchestrates the end to end haystack pipeline  
  connects retrievers, reranker, llm, fact checker, entities and relationships

- `models/`  
  wrappers around machine learning models  
  entity extraction, relationship extraction, reranking, nli, llm, answer checking

- `components/`  
  custom haystack components  
  cache checking, content extraction, document retrieval from chromadb, summarization, query expansion

- `data/`  
  storage and source integrations  
  sqlite database, chromadb document store, networkx graph, external web sources

## responsibilities

- receive high level query from flask frontend
- run multi source retrieval in parallel
- clean and split documents
- rank by relevance and diversity
- build prompts and call llm
- verify facts and extract entities and relationships
- return structured result to frontend and database