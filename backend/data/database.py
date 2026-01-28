"""
manage profiles database
store company profiles
support offline analytics
"""

import sqlite3
import json
import os
from datetime import datetime

from backend.configuration.paths import SQLITE_DB_PATH, STORES_DIR
from backend.configuration.sql import (
    PROFILES_CREATE_TABLE,
    PROFILES_INDEX_COMPANY,
    PROFILES_INSERT,
    PROFILES_SELECT_ALL,
    PROFILES_SELECT_RECENT,
    PROFILES_SELECT_BY_ID,
    PROFILES_DELETE_BY_ID,
    SQL_JSON_EMPTY_OBJECT,
    SQL_JSON_EMPTY_LIST,
)


# ==================== PROFILES DATABASE ====================

class ProfilesDatabase:

    def __init__(self, config=None):
        # store config for future use
        self.config = config

        # ensure stores directory exists
        os.makedirs(STORES_DIR, exist_ok=True)

        # open sqlite database connection
        self._init_sqlite()

        # create profiles tables
        self._init_tables()

    def _init_sqlite(self):
        # open sqlite database file
        os.makedirs(SQLITE_DB_PATH.parent, exist_ok=True)

        # open sqlite database connection
        self.conn = sqlite3.connect(str(SQLITE_DB_PATH), check_same_thread=False)

        # set row mapping
        self.conn.row_factory = sqlite3.Row

        # create cursor
        self.cursor = self.conn.cursor()

        # print status
        print(f"[PROFILES_DB] connected to: stores/{SQLITE_DB_PATH.name}")

    def _init_tables(self):
        # create profiles table and index
        self.cursor.execute(PROFILES_CREATE_TABLE)
        self.cursor.execute(PROFILES_INDEX_COMPANY)
        self.conn.commit()

        # apply schema updates
        self._migrate_tables()

    def _migrate_tables(self):
        # add missing columns
        self.cursor.execute("PRAGMA table_info(profiles)")
        rows = self.cursor.fetchall()

        # collect column names
        names = []
        for row in rows:
            # append column name
            names.append(str(row["name"]))

        # add documents column
        if "documents_json" not in names:
            self.cursor.execute("ALTER TABLE profiles ADD COLUMN documents_json TEXT")
            self.conn.commit()

        # fill null json blobs
        self.cursor.execute(
            f"UPDATE profiles SET customer_json = '{SQL_JSON_EMPTY_OBJECT}' "
            f"WHERE customer_json IS NULL OR customer_json = ''"
        )
        self.cursor.execute(
            f"UPDATE profiles SET corporate_guarantor_json = '{SQL_JSON_EMPTY_OBJECT}' "
            f"WHERE corporate_guarantor_json IS NULL OR corporate_guarantor_json = ''"
        )
        self.cursor.execute(
            f"UPDATE profiles SET high_risk_entities_json = '{SQL_JSON_EMPTY_LIST}' "
            f"WHERE high_risk_entities_json IS NULL OR high_risk_entities_json = ''"
        )
        self.cursor.execute(
            f"UPDATE profiles SET documents_json = '{SQL_JSON_EMPTY_LIST}' "
            f"WHERE documents_json IS NULL OR documents_json = ''"
        )
        self.conn.commit()

    def save_profile(
        self,
        company: str,
        snapshot: str,
        customer: dict,
        corporate_guarantor: dict,
        high_risk_entities: list,
        documents: list,
        confidence: float,
        created_at: str = None,
    ) -> int:
        # insert single profile record and return profile id
        if not company:
            return 0

        # normalize timestamp
        if created_at:
            created_str = str(created_at).strip()
        else:
            created_str = datetime.now().isoformat()

        # encode json fields
        customer_json = json.dumps(customer, ensure_ascii=False)
        corp_json = json.dumps(corporate_guarantor, ensure_ascii=False)
        high_risk_json = json.dumps(high_risk_entities, ensure_ascii=False)
        documents_json = json.dumps(documents, ensure_ascii=False)

        # normalize confidence
        conf_val = float(confidence)

        # write row
        self.cursor.execute(
            PROFILES_INSERT,
            (
                company,
                snapshot,
                customer_json,
                corp_json,
                high_risk_json,
                documents_json,
                conf_val,
                created_str,
            ),
        )

        # read id
        profile_id = self.cursor.lastrowid or 0

        # commit row
        self.conn.commit()
        return int(profile_id)

    def _row_to_profile_dict_brief(self, row) -> dict:
        # convert sqlite row to brief dict
        snapshot = row["snapshot"] or ""

        # parse json blobs
        customer = json.loads(row["customer_json"])
        corporate_guarantor = json.loads(row["corporate_guarantor_json"])
        high_risk_entities = json.loads(row["high_risk_entities_json"])

        # normalize confidence
        conf_val = 0.0
        if row["confidence"] is not None:
            conf_val = float(row["confidence"])

        return {
            "profile_id": int(row["profile_id"]),
            "company": row["company"],
            "snapshot": snapshot,
            "customer": customer,
            "corporate_guarantor": corporate_guarantor,
            "high_risk_entities": high_risk_entities,
            "confidence": conf_val,
            "created_at": row["created_at"],
        }

    def _row_to_profile_dict_full(self, row) -> dict:
        # convert sqlite row to full dict
        item = self._row_to_profile_dict_brief(row)

        # parse json blob
        documents = json.loads(row["documents_json"])

        # attach docs
        item["documents"] = documents
        return item

    def fetch_all_profiles(self) -> list:
        # fetch all profiles for offline analytics
        self.cursor.execute(PROFILES_SELECT_ALL)
        rows = self.cursor.fetchall()
        result = []

        for row in rows:
            # append row dict
            result.append(self._row_to_profile_dict_full(row))

        return result

    def fetch_recent_profiles(self, limit: int = 30) -> list:
        # fetch recent profiles for ui
        cap = int(limit)

        # fetch rows
        self.cursor.execute(PROFILES_SELECT_RECENT, (cap,))
        rows = self.cursor.fetchall()

        result = []
        for row in rows:
            # append row dict
            result.append(self._row_to_profile_dict_brief(row))

        return result

    def fetch_profile_by_id(self, profile_id: int) -> dict:
        # fetch single profile by id
        pid = int(profile_id)
        self.cursor.execute(PROFILES_SELECT_BY_ID, (pid,))
        row = self.cursor.fetchone()
        if not row:
            return {}
        return self._row_to_profile_dict_full(row)

    def delete_profile_by_id(self, profile_id: int) -> int:
        # delete single profile by id
        pid = int(profile_id)
        self.cursor.execute(PROFILES_DELETE_BY_ID, (pid,))
        affected = self.cursor.rowcount or 0
        self.conn.commit()
        return int(affected)

    def close(self):
        # close sqlite connection
        if getattr(self, "conn", None):
            self.conn.close()

    def __del__(self):
        # close sqlite on cleanup
        self.close()