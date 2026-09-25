import json
import time
from typing import Any

from sqlalchemy.orm import sessionmaker

from app.models.cache_entry import CacheEntry


class SQLiteCache:
    def __init__(self, sessions: sessionmaker, ttl_seconds: int):
        self.sessions = sessions
        self.ttl_seconds = ttl_seconds

    def get(self, key: str) -> Any | None:
        with self.sessions() as session:
            entry = session.get(CacheEntry, key)
            if entry is None:
                return None
            if entry.expires_at <= time.time():
                session.delete(entry)
                session.commit()
                return None
            return json.loads(entry.payload)

    def set(self, key: str, value: Any) -> None:
        payload = json.dumps(value, separators=(",", ":"))
        with self.sessions.begin() as session:
            entry = session.get(CacheEntry, key)
            if entry is None:
                entry = CacheEntry(key=key, payload=payload, expires_at=time.time() + self.ttl_seconds)
                session.add(entry)
            else:
                entry.payload = payload
                entry.expires_at = time.time() + self.ttl_seconds
