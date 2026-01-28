"""
centralize entity and relationship labels
define extraction categories
provide label utilities
"""

# ==================== ENTITY LABELS ====================

# gliner entity extraction labels
ENTITY_LABELS = [
    "PERSON",
    "ORG"
]


# ==================== RELATIONSHIP LABELS ====================

# glirel relationship extraction labels
RELATIONSHIP_LABELS = [
    "works for",
    "employs",
    "subsidiary of",
    "parent company of",
    "owns",
    "owned by",
    "partner of",
    "affiliated with",
    "collaborates with",
    "investor in",
    "funded by",
    "acquired by",
    "acquires",
    "merged with",
    "supplies to",
    "customer of",
    "competitor of",
    "board member of",
    "director of",
    "chairperson of",
    "CEO of",
    "founded by",
    "advises",
    "regulates",
    "regulated by",
    "member of",
    "represents",
    "sponsors",
    "related to"
]


# ==================== QUERY ENTITY LABELS ====================

# labels for extracting entities from queries
QUERY_ENTITY_LABELS = [
    "PERSON",
    "ORG"
]