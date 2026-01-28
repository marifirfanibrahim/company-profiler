"""
sql configuration
define schemas
store statements
"""

# ==================== JSON ====================

SQL_JSON_EMPTY_OBJECT = "{}"                             # default {}, json object text
SQL_JSON_EMPTY_LIST = "[]"                               # default [], json list text


# ==================== PROFILES TABLE ====================

PROFILES_CREATE_TABLE = f"""
CREATE TABLE IF NOT EXISTS profiles (
    profile_id INTEGER PRIMARY KEY AUTOINCREMENT,
    company TEXT NOT NULL,
    snapshot TEXT,
    customer_json TEXT DEFAULT '{SQL_JSON_EMPTY_OBJECT}',
    corporate_guarantor_json TEXT DEFAULT '{SQL_JSON_EMPTY_OBJECT}',
    high_risk_entities_json TEXT DEFAULT '{SQL_JSON_EMPTY_LIST}',
    documents_json TEXT DEFAULT '{SQL_JSON_EMPTY_LIST}',
    confidence REAL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
)
"""

PROFILES_INDEX_COMPANY = """
CREATE INDEX IF NOT EXISTS idx_profiles_company ON profiles(company)
"""

PROFILES_INSERT = """
INSERT INTO profiles
    (company, snapshot, customer_json, corporate_guarantor_json, high_risk_entities_json, documents_json, confidence, created_at)
VALUES (?, ?, ?, ?, ?, ?, ?, ?)
"""

PROFILES_SELECT_ALL = """
SELECT
    profile_id,
    company,
    snapshot,
    customer_json,
    corporate_guarantor_json,
    high_risk_entities_json,
    documents_json,
    confidence,
    created_at
FROM profiles
ORDER BY created_at DESC, profile_id DESC
"""

PROFILES_SELECT_RECENT = """
SELECT
    profile_id,
    company,
    snapshot,
    customer_json,
    corporate_guarantor_json,
    high_risk_entities_json,
    confidence,
    created_at
FROM profiles
ORDER BY created_at DESC, profile_id DESC
LIMIT ?
"""

PROFILES_SELECT_BY_ID = """
SELECT
    profile_id,
    company,
    snapshot,
    customer_json,
    corporate_guarantor_json,
    high_risk_entities_json,
    documents_json,
    confidence,
    created_at
FROM profiles
WHERE profile_id = ?
"""

PROFILES_DELETE_BY_ID = """
DELETE FROM profiles
WHERE profile_id = ?
"""