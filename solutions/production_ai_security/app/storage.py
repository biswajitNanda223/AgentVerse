from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any, cast

import psycopg
import redis


class DurableSecurityStore:
    """Transactional local store mirroring the Postgres production schema."""

    def __init__(self, path: str | Path) -> None:
        self._path = str(path)
        with self._connect() as connection:
            connection.executescript(
                """
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS security_events (
                  sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                  tenant_id TEXT NOT NULL,
                  event_type TEXT NOT NULL,
                  payload TEXT NOT NULL,
                  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS security_events_tenant
                  ON security_events(tenant_id, sequence);
                CREATE TABLE IF NOT EXISTS consumed_nonces (
                  tenant_id TEXT NOT NULL,
                  nonce TEXT NOT NULL,
                  PRIMARY KEY (tenant_id, nonce)
                );
                CREATE TABLE IF NOT EXISTS secure_cache (
                  cache_key TEXT PRIMARY KEY,
                  tenant_id TEXT NOT NULL,
                  value TEXT NOT NULL,
                  expires_at INTEGER NOT NULL
                );
                """
            )

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self._path)
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def append_event(self, tenant_id: str, event_type: str, payload: dict[str, Any]) -> int:
        with self._connect() as connection:
            cursor = connection.execute(
                "INSERT INTO security_events(tenant_id,event_type,payload) VALUES(?,?,?)",
                (tenant_id, event_type, json.dumps(payload, sort_keys=True)),
            )
            if cursor.lastrowid is None:
                raise RuntimeError("event insert returned no sequence")
            return int(cursor.lastrowid)

    def events(self, tenant_id: str) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT sequence,event_type,payload,created_at FROM security_events "
                "WHERE tenant_id=? ORDER BY sequence",
                (tenant_id,),
            ).fetchall()
        return [
            {
                "sequence": row[0],
                "event_type": row[1],
                "payload": json.loads(row[2]),
                "created_at": row[3],
            }
            for row in rows
        ]

    def consume_nonce(self, tenant_id: str, nonce: str) -> bool:
        try:
            with self._connect() as connection:
                connection.execute(
                    "INSERT INTO consumed_nonces(tenant_id,nonce) VALUES(?,?)",
                    (tenant_id, nonce),
                )
        except sqlite3.IntegrityError:
            return False
        return True


class PostgresSecurityStore:
    """Durable multi-replica event and nonce store for production."""

    def __init__(self, dsn: str) -> None:
        self._dsn = dsn

    def migrate(self) -> None:
        with psycopg.connect(self._dsn) as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS security_events (
                  sequence BIGSERIAL PRIMARY KEY,
                  tenant_id TEXT NOT NULL,
                  event_type TEXT NOT NULL,
                  payload JSONB NOT NULL,
                  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                CREATE INDEX IF NOT EXISTS security_events_tenant
                  ON security_events(tenant_id, sequence);
                CREATE TABLE IF NOT EXISTS consumed_nonces (
                  tenant_id TEXT NOT NULL,
                  nonce TEXT NOT NULL,
                  PRIMARY KEY (tenant_id, nonce)
                );
                """
            )

    def append_event(self, tenant_id: str, event_type: str, payload: dict[str, Any]) -> int:
        with psycopg.connect(self._dsn) as connection, connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO security_events(tenant_id,event_type,payload) "
                "VALUES(%s,%s,%s) RETURNING sequence",
                (tenant_id, event_type, json.dumps(payload)),
            )
            row = cursor.fetchone()
            if row is None:
                raise RuntimeError("event insert returned no sequence")
            return int(row[0])

    def consume_nonce(self, tenant_id: str, nonce: str) -> bool:
        with psycopg.connect(self._dsn) as connection, connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO consumed_nonces(tenant_id,nonce) VALUES(%s,%s) "
                "ON CONFLICT DO NOTHING RETURNING nonce",
                (tenant_id, nonce),
            )
            return cursor.fetchone() is not None


class RedisTenantCache:
    """Shared TTL cache retaining tenant ownership for targeted invalidation."""

    def __init__(self, url: str, *, ttl_seconds: int = 300) -> None:
        self._client = redis.Redis.from_url(url, decode_responses=True)
        self._ttl = ttl_seconds

    def get(self, key: str) -> dict[str, Any] | None:
        value = cast(str | None, self._client.get(key))
        return json.loads(value) if value else None

    def put(self, key: str, tenant_id: str, value: dict[str, Any]) -> None:
        pipeline = self._client.pipeline()
        pipeline.setex(key, self._ttl, json.dumps(value, sort_keys=True))
        pipeline.sadd(f"tenant-cache:{tenant_id}", key)
        pipeline.expire(f"tenant-cache:{tenant_id}", self._ttl)
        pipeline.execute()

    def invalidate_tenant(self, tenant_id: str) -> int:
        index = f"tenant-cache:{tenant_id}"
        keys = list(cast(set[str], self._client.smembers(index)))
        if not keys:
            return 0
        return int(cast(int, self._client.delete(*keys, index)))
