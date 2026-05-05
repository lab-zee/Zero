"""
Postgres-backed tool call cache. Persists across restarts and deploys.
"""

import hashlib
import json
import random
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import text

from ...database import SessionLocal

# TTL in seconds per tool. Tools not listed here are never cached.
CACHE_TTL = {
    "web_search": 7 * 86400,                # 7 days
    "news_search": 7 * 86400,               # 7 days
    "scrape_website": 2 * 86400,             # 2 days
    "calculator": 30 * 86400,               # 30 days
    "extract_citations": 86400,              # 1 day
    "extract_citations_structured": 86400,   # 1 day
}

MAX_ENTRIES = 1000


class ToolCache:
    def __init__(self):
        self.last_hit = False

    @staticmethod
    def _make_key(tool_name: str, arguments: dict) -> str:
        raw = tool_name + json.dumps(arguments, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode()).hexdigest()

    def get(self, tool_name: str, arguments: dict) -> Optional[str]:
        if tool_name not in CACHE_TTL:
            self.last_hit = False
            return None

        key = self._make_key(tool_name, arguments)
        now = datetime.now(timezone.utc)

        try:
            db = SessionLocal()
            try:
                row = db.execute(
                    text("SELECT result FROM tool_cache WHERE key = :key AND expires_at > :now"),
                    {"key": key, "now": now},
                ).fetchone()

                # Lazy cleanup: ~5% of calls
                if random.random() < 0.05:
                    self._cleanup(db)

                if row:
                    self.last_hit = True
                    return row[0]

                self.last_hit = False
                return None
            finally:
                db.close()
        except Exception:
            self.last_hit = False
            return None

    def set(self, tool_name: str, arguments: dict, result: str):
        ttl = CACHE_TTL.get(tool_name)
        if ttl is None:
            return

        key = self._make_key(tool_name, arguments)
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=ttl)

        try:
            db = SessionLocal()
            try:
                # Upsert: insert or update on conflict
                db.execute(
                    text("""
                        INSERT INTO tool_cache (key, tool_name, result, created_at, expires_at)
                        VALUES (:key, :tool_name, :result, :created_at, :expires_at)
                        ON CONFLICT (key) DO UPDATE SET
                            result = EXCLUDED.result,
                            created_at = EXCLUDED.created_at,
                            expires_at = EXCLUDED.expires_at
                    """),
                    {"key": key, "tool_name": tool_name, "result": result,
                     "created_at": now, "expires_at": expires_at},
                )
                db.commit()
            finally:
                db.close()
        except Exception:
            pass

    def _cleanup(self, db):
        try:
            # Remove expired entries
            db.execute(
                text("DELETE FROM tool_cache WHERE expires_at <= :now"),
                {"now": datetime.now(timezone.utc)},
            )
            # Enforce max size by removing oldest entries beyond limit
            db.execute(
                text("""
                    DELETE FROM tool_cache WHERE key IN (
                        SELECT key FROM tool_cache ORDER BY created_at DESC OFFSET :max_entries
                    )
                """),
                {"max_entries": MAX_ENTRIES},
            )
            db.commit()
        except Exception:
            pass


tool_cache = ToolCache()
