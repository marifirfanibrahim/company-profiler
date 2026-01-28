"""
routes module initialization
export all blueprint objects
"""

from .main import main_bp
from .search import search_bp

__all__ = ['main_bp', 'search_bp']