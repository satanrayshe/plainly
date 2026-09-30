"""Rate limits, the global daily cap and anonymous counters, all in one DynamoDB table.

Items (partition key "id"):
  rl#<route>#<ip hash>#<hour>   per-IP hourly window, TTL attribute expiresAt
  cap#<route>#<YYYY-MM-DD>      global daily cap, TTL attribute expiresAt
  stats                         anonymous counters, no TTL
IPs are stored only as a salted hash prefix.
"""
import hashlib
import json
import os
import threading
import time
from datetime import datetime, timezone

STATS_ID = "stats"


def ip_hash(ip):
    salt = os.environ.get("IP_HASH_SALT", "plainly")
    return hashlib.sha256(f"{salt}|{ip}".encode()).hexdigest()[:16]


def hour_window(now=None):
    return int((now or time.time()) // 3600)


def utc_day(now=None):
    return datetime.fromtimestamp(now or time.time(), tz=timezone.utc).strftime("%Y-%m-%d")


def _error_code(exc):
    return getattr(exc, "response", {}).get("Error", {}).get("Code", "")


class DynamoCounters:
    def __init__(self, table):
        self.table = table

    def take(self, key, limit, expires_at):
        """Count one use of `key`. False when the limit is already reached (the use is then not counted)."""
        try:
            self.table.update_item(
                Key={"id": key},
                UpdateExpression="ADD hits :one SET expiresAt = :exp",
                ConditionExpression="attribute_not_exists(hits) OR hits < :limit",
                ExpressionAttributeValues={":one": 1, ":exp": int(expires_at), ":limit": int(limit)},
            )
            return True
        except Exception as exc:  # noqa: BLE001
            if _error_code(exc) == "ConditionalCheckFailedException":
                return False
            # Fail open: never block people because the limiter itself is broken. The daily cap and the
            # AWS Budget alarm remain as backstops.
            print(json.dumps({"level": "warning", "event": "limiter_error", "error": type(exc).__name__}))
            return True

    def bump(self, names):
        if not names:
            return
        try:
            self.table.update_item(
                Key={"id": STATS_ID},
                UpdateExpression="ADD " + ", ".join(f"#c{i} :one" for i in range(len(names))),
                ExpressionAttributeNames={f"#c{i}": name for i, name in enumerate(names)},
                ExpressionAttributeValues={":one": 1},
            )
        except Exception as exc:  # noqa: BLE001 - counters are nice to have, never worth a failed request
            print(json.dumps({"level": "warning", "event": "stats_error", "error": type(exc).__name__}))

    def read(self):
        item = self.table.get_item(Key={"id": STATS_ID}).get("Item") or {}
        return {k: int(v) for k, v in item.items() if k != "id"}


class MemoryCounters:
    """Same interface, in process memory. Used by the dev server and when no table is configured."""

    def __init__(self):
        self.values = {}
        self.lock = threading.Lock()

    def take(self, key, limit, expires_at):
        with self.lock:
            if self.values.get(key, 0) >= limit:
                return False
            self.values[key] = self.values.get(key, 0) + 1
            return True

    def bump(self, names):
        with self.lock:
            for name in names:
                self.values[f"{STATS_ID}#{name}"] = self.values.get(f"{STATS_ID}#{name}", 0) + 1

    def read(self):
        prefix = f"{STATS_ID}#"
        return {k[len(prefix):]: v for k, v in self.values.items() if k.startswith(prefix)}
