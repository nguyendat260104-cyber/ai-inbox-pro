"""Small, dependency-free protections for inbound webhook and widget traffic."""

from __future__ import annotations

import hashlib
import hmac
import json
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Optional

from ai_inbox.core.db import get_connection


def verify_hmac_sha256(raw_body: bytes, provided_signature: str, secret: str, prefix: str = "sha256=") -> bool:
    """Compare a provider HMAC without exposing the secret or accepting blanks."""
    if not raw_body or not provided_signature or not secret:
        return False
    expected = prefix + hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(provided_signature, expected)


class TokenBucketRateLimiter:
    """Thread-safe token bucket keyed by workspace or client address."""

    def __init__(self, capacity: int = 60, refill_per_second: float = 1.0):
        self.capacity = capacity
        self.refill_per_second = refill_per_second
        self._buckets: Dict[str, tuple[float, float]] = {}
        self._lock = threading.Lock()

    def allow(self, key: str, tokens: float = 1.0, now: Optional[float] = None) -> bool:
        import time
        timestamp = time.monotonic() if now is None else now
        with self._lock:
            available, last_seen = self._buckets.get(key, (float(self.capacity), timestamp))
            available = min(self.capacity, available + (timestamp - last_seen) * self.refill_per_second)
            if available < tokens:
                self._buckets[key] = (available, timestamp)
                return False
            self._buckets[key] = (available - tokens, timestamp)
            return True


class EventDeduplicator:
    """SQLite-backed dedupe window for provider retries and replayed deliveries."""

    def __init__(self, db_path: Optional[Path] = None, window_minutes: int = 10):
        self.db_path = db_path
        self.window_minutes = window_minutes

    def seen(self, workspace_id: str, provider: str, event_id: str) -> bool:
        if not event_id:
            return False
        now = datetime.now(timezone.utc)
        cutoff = (now - timedelta(minutes=self.window_minutes)).isoformat()
        details = json.dumps({"provider": provider, "event_id": event_id}, sort_keys=True)
        conn = get_connection(self.db_path)
        try:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                """SELECT 1 FROM activity_logs
                   WHERE workspace_id = ? AND event_type = 'webhook_received'
                     AND details_json = ? AND timestamp >= ? LIMIT 1""",
                (workspace_id, details, cutoff),
            ).fetchone()
            if row:
                conn.commit()
                return True
            conn.execute(
                """INSERT INTO activity_logs (id, workspace_id, event_type, details_json, timestamp)
                   VALUES (?, ?, 'webhook_received', ?, ?)""",
                (__import__("uuid").uuid4().hex, workspace_id, details, now.isoformat()),
            )
            conn.commit()
            return False
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
