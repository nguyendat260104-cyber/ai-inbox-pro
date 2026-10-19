#!/usr/bin/env python3
"""Focused tests for request verification, throttling and event deduplication."""

import hashlib
import hmac
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from ai_inbox.core.db import get_connection, init_db
from ai_inbox.core.middleware import EventDeduplicator, TokenBucketRateLimiter, verify_hmac_sha256


def run_tests() -> None:
    body, secret = b'{"event":"hello"}', "test-secret"
    signature = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    assert verify_hmac_sha256(body, signature, secret)
    assert not verify_hmac_sha256(body, signature, "wrong-secret")

    limiter = TokenBucketRateLimiter(capacity=2, refill_per_second=1)
    assert limiter.allow("ws", now=0)
    assert limiter.allow("ws", now=0)
    assert not limiter.allow("ws", now=0)
    assert limiter.allow("ws", now=1)

    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "inbox.db"
        init_db(db_path)
        conn = get_connection(db_path)
        conn.execute(
            "INSERT INTO workspaces (id, name, slug, created_at) VALUES ('ws-1', 'Test', 'middleware-test', ?)",
            (datetime.now(timezone.utc).isoformat(),),
        )
        conn.commit()
        conn.close()
        dedupe = EventDeduplicator(db_path)
        assert not dedupe.seen("ws-1", "facebook", "evt-1")
        assert dedupe.seen("ws-1", "facebook", "evt-1")
        assert not dedupe.seen("ws-1", "facebook", "evt-2")

    print("middleware tests passed")


if __name__ == "__main__":
    run_tests()
