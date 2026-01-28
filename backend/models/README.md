# backend / models

ai model wrappers used by the main pipeline.
reads model configuration from `configuration/models.py`

## files

- `entity_extractor.py`  
  wraps gliner ner model  
  extracts person and organization entities from text  
  deduplicates similar names

- `relationship_extractor.py`  
  wraps glirel relation extraction model  
  finds relationships between extracted entities  
  filters by confidence and stopwords

- `fact_checker.py`  
  wraps multilingual nli model  
  verifies each summary line against cited documents  
  accepts entailment and neutral, rejects strong contradictions  
  returns per fact confidence scores

- `reranker.py`  
  wraps cross encoder model  
  scores query document pairs  
  filters low relevance results  
  applies domain diversity penalty

- `generator.py`  
  creates haystack generators for ollama, openai, and  providers  

- `answer_checker.py`  
  uses llm as judge  
  scores how well summary answers original query  
  returns answer score and short reason

- `__init__.py`  
  exports all model classes and factory helpers