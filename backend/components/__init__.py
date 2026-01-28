"""
components module
haystack pipeline components
"""

# import component classes
from .content_extractor import ContentExtractor
from .document_retriever import DocumentStoreRetriever

# export list
__all__ = [
    'ContentExtractor',
    'DocumentStoreRetriever',
]