"""Minimal, auditable project-state library using only the Python standard library.

This is an MVP, not a production ERP subsystem. It provides atomic state transitions,
immutable evidence/events, optimistic concurrency, hash-chain integrity checks,
and atomic JSON snapshot export.
"""
from __future__ import annotations

import hashlib
from contextlib import contextmanager
import json
import os
import sqlite3
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

SCHEMA_VERSION = 1
IMPLEMENTATION_STATES = {"PLANNED", "IN_PROGRESS", "IMPLEMENTED", "BLOCKED", "UNKNOWN"}
VERIFICATION_STATES = {"NOT_VERIFIED", "RUNNING", "PARTIALLY_VERIFIED", "VERIFIED", "FAILED"}
RELEASE_STATES = {"NOT_RELEASED", "CANDIDATE", "RELEASED"}

TRANSITIONS = {
    "implementation_status": {
        "PLANNED": {"IN_PROGRESS", "BLOCKED", "UNKNOWN"},
        "IN_PROGRESS": {"IMPLEMENTED", "BLOCKED", "UNKNOWN"},
        "IMPLEMENTED": {"IN_PROGRESS", "BLOCKED", "UNKNOWN"},
        "BLOCKED": {"IN_PROGRESS", "UNKNOWN"},
        "UNKNOWN": {"PLANNED", "IN_PROGRESS", "BLOCKED"},
    },
    "verification_status": {
        "NOT_VERIFIED": {"RUNNING", "PARTIALLY_VERIFIED", "FAILED"},
        "RUNNING": {"VERIFIED", "PARTIALLY_VERIFIED", "FAILED"},
        "PARTIALLY_VERIFIED": {"RUNNING", "VERIFIED", "FAILED"},
        "VERIFIED": {"NOT_VERIFIED", "RUNNING", "FAILED"},
        "FAILED": {"RUNNING", "NOT_VERIFIED"},
    },
    "release_status": {
        "NOT_RELEASED": {"CANDIDATE"},
        "CANDIDATE": {"RELEASED", "NOT_RELEASED"},
        "RELEASED": {"NOT_RELEASED"},
    },
}

class StateLibraryError(Exception):
    """Base error for the library."""

class NotFound(StateLibraryError):
    pass

class InvalidTransition(StateLibraryError):
    pass

class VersionConflict(StateLibraryError):
    pass

class IdempotencyConflict(StateLibraryError):
    pass

class EvidenceRequired(StateLibraryError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _hash_event(previous_hash: str, payload_json: str) -> str:
    return hashlib.sha256((previous_hash + "\n" + payload_json).encode("utf-8")).hexdigest()


class StateLibrary:
    """SQLite-backed state registry. Use one instance per database path."""

    def __init__(self, database: str | os.PathLike[str]):
        self.database = str(database)
        if self.database != ":memory:":
            Path(self.database).parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.database, timeout=10, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA busy_timeout = 10000")
        return conn

    @contextmanager
    def _connection(self):
        conn = self._connect()
        try:
            yield conn
        finally:
            conn.close()

    def _initialize(self) -> None:
        with self._connection() as conn:
            conn.execute("PRAGMA journal_mode = WAL")
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS components (
                    component_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    component_type TEXT NOT NULL,
                    implementation_status TEXT NOT NULL,
                    verification_status TEXT NOT NULL,
                    release_status TEXT NOT NULL,
                    source_commit TEXT,
                    version INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS events (
                    seq INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT NOT NULL UNIQUE,
                    component_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    version_before INTEGER,
                    version_after INTEGER NOT NULL,
                    payload_json TEXT NOT NULL,
                    previous_hash TEXT NOT NULL,
                    event_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(component_id) REFERENCES components(component_id)
                );
                CREATE TABLE IF NOT EXISTS evidence (
                    evidence_id TEXT PRIMARY KEY,
                    event_id TEXT NOT NULL,
                    component_id TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    claim TEXT NOT NULL,
                    source_ref TEXT NOT NULL,
                    commit_id TEXT,
                    environment_id TEXT,
                    result TEXT NOT NULL,
                    observed_at TEXT NOT NULL,
                    validity_scope_json TEXT NOT NULL,
                    FOREIGN KEY(event_id) REFERENCES events(event_id),
                    FOREIGN KEY(component_id) REFERENCES components(component_id)
                );
                CREATE TRIGGER IF NOT EXISTS events_no_update
                BEFORE UPDATE ON events BEGIN SELECT RAISE(ABORT, 'events are append-only'); END;
                CREATE TRIGGER IF NOT EXISTS events_no_delete
                BEFORE DELETE ON events BEGIN SELECT RAISE(ABORT, 'events are append-only'); END;
                CREATE TRIGGER IF NOT EXISTS evidence_no_update
                BEFORE UPDATE ON evidence BEGIN SELECT RAISE(ABORT, 'evidence is immutable'); END;
                CREATE TRIGGER IF NOT EXISTS evidence_no_delete
                BEFORE DELETE ON evidence BEGIN SELECT RAISE(ABORT, 'evidence is immutable'); END;
            """)

    def _head_hash(self, conn: sqlite3.Connection) -> str:
        row = conn.execute("SELECT event_hash FROM events ORDER BY seq DESC LIMIT 1").fetchone()
        return row["event_hash"] if row else "GENESIS"

    def _append_event(self, conn: sqlite3.Connection, event_id: str, component_id: str,
                      event_type: str, version_before: int | None, version_after: int,
                      payload: Mapping[str, Any], created_at: str) -> None:
        payload_json = _canonical(dict(payload))
        previous_hash = self._head_hash(conn)
        event_hash = _hash_event(previous_hash, payload_json)
        conn.execute(
            "INSERT INTO events(event_id, component_id, event_type, version_before, version_after, payload_json, previous_hash, event_hash, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (event_id, component_id, event_type, version_before, version_after, payload_json, previous_hash, event_hash, created_at),
        )

    def _component_row(self, conn: sqlite3.Connection, component_id: str) -> sqlite3.Row:
        row = conn.execute("SELECT * FROM components WHERE component_id = ?", (component_id,)).fetchone()
        if row is None:
            raise NotFound(f"Component not found: {component_id}")
        return row

    @staticmethod
    def _as_dict(row: sqlite3.Row) -> dict[str, Any]:
        return dict(row)

    def create_component(self, component_id: str, name: str, component_type: str = "erp_module",
                         source_commit: str | None = None, event_id: str | None = None) -> dict[str, Any]:
        if not component_id.strip() or not name.strip() or not component_type.strip():
            raise ValueError("component_id, name and component_type must be non-empty")
        event_id = event_id or str(uuid.uuid4())
        created_at = _now()
        initial = {
            "component_id": component_id, "name": name, "component_type": component_type,
            "implementation_status": "PLANNED", "verification_status": "NOT_VERIFIED",
            "release_status": "NOT_RELEASED", "source_commit": source_commit,
            "version": 1, "created_at": created_at, "updated_at": created_at,
        }
        request = {"component_id": component_id, "name": name, "component_type": component_type, "source_commit": source_commit}
        payload = {"event_id": event_id, "event_type": "COMPONENT_CREATED", "component": initial, "request": request}
        with self._connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            duplicate = conn.execute("SELECT payload_json FROM events WHERE event_id = ?", (event_id,)).fetchone()
            if duplicate:
                existing_payload = json.loads(duplicate["payload_json"])
                if existing_payload.get("request") != request:
                    conn.rollback()
                    raise IdempotencyConflict(f"event_id reused with different content: {event_id}")
                existing = conn.execute("SELECT * FROM components WHERE component_id = ?", (component_id,)).fetchone()
                conn.commit()
                if existing is None:
                    raise StateLibraryError("Idempotent event exists but its component is missing")
                return self._as_dict(existing)
            try:
                conn.execute(
                    "INSERT INTO components(component_id,name,component_type,implementation_status,verification_status,release_status,source_commit,version,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
                    tuple(initial[k] for k in ("component_id","name","component_type","implementation_status","verification_status","release_status","source_commit","version","created_at","updated_at")),
                )
            except sqlite3.IntegrityError as exc:
                conn.rollback()
                raise StateLibraryError(f"Component already exists or violates schema: {component_id}") from exc
            self._append_event(conn, event_id, component_id, "COMPONENT_CREATED", None, 1, payload, created_at)
            conn.commit()
        return initial

    def transition(self, component_id: str, expected_version: int, changes: Mapping[str, Any],
                   reason: str, event_id: str | None = None,
                   evidence: Mapping[str, Any] | None = None) -> dict[str, Any]:
        allowed_fields = set(TRANSITIONS) | {"source_commit"}
        if not changes or set(changes) - allowed_fields:
            raise ValueError(f"changes must contain allowed fields only: {sorted(allowed_fields)}")
        if not reason.strip():
            raise ValueError("A non-empty reason is required")
        event_id = event_id or str(uuid.uuid4())
        evidence_data = dict(evidence) if evidence is not None else None
        with self._connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            duplicate = conn.execute("SELECT component_id, payload_json FROM events WHERE event_id = ?", (event_id,)).fetchone()
            if duplicate:
                existing_payload = json.loads(duplicate["payload_json"])
                requested = {"component_id": component_id, "expected_version": expected_version,
                             "changes": dict(changes), "reason": reason, "evidence": evidence_data}
                if existing_payload.get("request") != requested:
                    conn.rollback()
                    raise IdempotencyConflict(f"event_id reused with different content: {event_id}")
                row = self._component_row(conn, component_id)
                conn.commit()
                return self._as_dict(row)

            row = self._component_row(conn, component_id)
            current = self._as_dict(row)
            if current["version"] != expected_version:
                conn.rollback()
                raise VersionConflict(f"Expected version {expected_version}; current version is {current['version']}")
            next_state = dict(current)
            for field, value in changes.items():
                if field in TRANSITIONS:
                    allowed_states = {"implementation_status": IMPLEMENTATION_STATES,
                                      "verification_status": VERIFICATION_STATES,
                                      "release_status": RELEASE_STATES}[field]
                    if value not in allowed_states:
                        raise InvalidTransition(f"Unknown {field}: {value}")
                    old_value = current[field]
                    if value != old_value and value not in TRANSITIONS[field][old_value]:
                        raise InvalidTransition(f"Forbidden {field} transition: {old_value} -> {value}")
                elif field == "source_commit" and value is not None and not isinstance(value, str):
                    raise ValueError("source_commit must be a string or null")
                next_state[field] = value

            commit_changed = "source_commit" in changes and changes["source_commit"] != current["source_commit"]
            if commit_changed:
                # Code provenance changes invalidate verification and release state automatically.
                if "verification_status" in changes and changes["verification_status"] != "NOT_VERIFIED":
                    raise InvalidTransition("Changing source_commit invalidates verification; verify in a separate event")
                if "release_status" in changes and changes["release_status"] != "NOT_RELEASED":
                    raise InvalidTransition("Changing source_commit invalidates release; release in a separate event")
                next_state["verification_status"] = "NOT_VERIFIED"
                next_state["release_status"] = "NOT_RELEASED"

            if next_state["verification_status"] == "VERIFIED" and current["verification_status"] != "VERIFIED":
                self._require_evidence(evidence_data, "TEST_RUN", "PASS", next_state["source_commit"])
            if next_state["release_status"] == "RELEASED" and current["release_status"] != "RELEASED":
                if next_state["verification_status"] != "VERIFIED":
                    raise EvidenceRequired("A component cannot be RELEASED unless verification_status is VERIFIED")
                self._require_evidence(evidence_data, "RELEASE", "PASS", next_state["source_commit"])

            created_at = _now()
            next_state["version"] = current["version"] + 1
            next_state["updated_at"] = created_at
            request = {"component_id": component_id, "expected_version": expected_version,
                       "changes": dict(changes), "reason": reason, "evidence": evidence_data}
            payload = {"event_id": event_id, "event_type": "STATE_TRANSITION", "component_id": component_id,
                       "version_before": current["version"], "version_after": next_state["version"],
                       "changes": dict(changes), "effective_state": next_state, "reason": reason,
                       "evidence": evidence_data, "request": request, "created_at": created_at}
            conn.execute(
                "UPDATE components SET implementation_status=?, verification_status=?, release_status=?, source_commit=?, version=?, updated_at=? WHERE component_id=? AND version=?",
                (next_state["implementation_status"], next_state["verification_status"], next_state["release_status"],
                 next_state["source_commit"], next_state["version"], created_at, component_id, expected_version),
            )
            if conn.total_changes == 0:
                conn.rollback()
                raise VersionConflict("Concurrent update detected")
            self._append_event(conn, event_id, component_id, "STATE_TRANSITION", current["version"], next_state["version"], payload, created_at)
            if evidence_data is not None:
                self._insert_evidence(conn, event_id, component_id, evidence_data, created_at)
            conn.commit()
            return next_state

    @staticmethod
    def _require_evidence(evidence: Mapping[str, Any] | None, kind: str, result: str,
                          source_commit: str | None) -> None:
        if evidence is None:
            raise EvidenceRequired(f"Transition requires {kind} evidence with result {result}")
        required = {"kind", "claim", "source_ref", "result"}
        if not required.issubset(evidence):
            raise EvidenceRequired(f"Evidence requires fields: {sorted(required)}")
        if evidence["kind"] != kind or evidence["result"] != result:
            raise EvidenceRequired(f"Expected evidence kind={kind} and result={result}")
        if source_commit is not None and evidence.get("commit_id") != source_commit:
            raise EvidenceRequired("Evidence commit_id must match the component source_commit")
        if not str(evidence["source_ref"]).strip() or not str(evidence["claim"]).strip():
            raise EvidenceRequired("Evidence claim and source_ref must be non-empty")

    def _insert_evidence(self, conn: sqlite3.Connection, event_id: str, component_id: str,
                         evidence: Mapping[str, Any], observed_at: str) -> None:
        required = {"kind", "claim", "source_ref", "result"}
        if not required.issubset(evidence):
            raise EvidenceRequired(f"Evidence requires fields: {sorted(required)}")
        evidence_id = str(evidence.get("evidence_id") or uuid.uuid4())
        scope = evidence.get("validity_scope", {})
        conn.execute(
            "INSERT INTO evidence(evidence_id,event_id,component_id,kind,claim,source_ref,commit_id,environment_id,result,observed_at,validity_scope_json) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (evidence_id, event_id, component_id, str(evidence["kind"]), str(evidence["claim"]),
             str(evidence["source_ref"]), evidence.get("commit_id"), evidence.get("environment_id"),
             str(evidence["result"]), str(evidence.get("observed_at") or observed_at), _canonical(scope)),
        )

    def get_component(self, component_id: str) -> dict[str, Any]:
        with self._connection() as conn:
            return self._as_dict(self._component_row(conn, component_id))

    def list_components(self) -> list[dict[str, Any]]:
        with self._connection() as conn:
            rows = conn.execute("SELECT * FROM components ORDER BY component_id").fetchall()
            return [self._as_dict(row) for row in rows]

    def list_events(self, component_id: str | None = None) -> list[dict[str, Any]]:
        with self._connection() as conn:
            if component_id is None:
                rows = conn.execute("SELECT * FROM events ORDER BY seq").fetchall()
            else:
                rows = conn.execute("SELECT * FROM events WHERE component_id=? ORDER BY seq", (component_id,)).fetchall()
            result = []
            for row in rows:
                item = dict(row)
                item["payload"] = json.loads(item.pop("payload_json"))
                result.append(item)
            return result

    def list_evidence(self, component_id: str | None = None) -> list[dict[str, Any]]:
        with self._connection() as conn:
            if component_id is None:
                rows = conn.execute("SELECT * FROM evidence ORDER BY observed_at, evidence_id").fetchall()
            else:
                rows = conn.execute("SELECT * FROM evidence WHERE component_id=? ORDER BY observed_at, evidence_id", (component_id,)).fetchall()
            result = []
            for row in rows:
                item = dict(row)
                item["validity_scope"] = json.loads(item.pop("validity_scope_json"))
                result.append(item)
            return result

    def verify_integrity(self) -> dict[str, Any]:
        """Verify the append-only event hash chain and event sequence links."""
        with self._connection() as conn:
            rows = conn.execute("SELECT seq,event_id,previous_hash,event_hash,payload_json FROM events ORDER BY seq").fetchall()
        previous = "GENESIS"
        checked = 0
        for row in rows:
            if row["previous_hash"] != previous:
                return {"valid": False, "events_checked": checked, "failed_seq": row["seq"], "reason": "previous_hash_mismatch"}
            expected = _hash_event(previous, row["payload_json"])
            if row["event_hash"] != expected:
                return {"valid": False, "events_checked": checked, "failed_seq": row["seq"], "reason": "event_hash_mismatch"}
            previous = row["event_hash"]
            checked += 1
        return {"valid": True, "events_checked": checked, "head_hash": previous}

    def verify_projection_consistency(self) -> dict[str, Any]:
        """Compare each current component projection with its latest committed event."""
        compared_fields = (
            "component_id", "name", "component_type", "implementation_status",
            "verification_status", "release_status", "source_commit", "version",
            "created_at", "updated_at",
        )
        with self._connection() as conn:
            components = conn.execute("SELECT * FROM components ORDER BY component_id").fetchall()
            events = conn.execute("SELECT component_id,event_type,payload_json,version_after FROM events ORDER BY seq").fetchall()
        latest: dict[str, dict[str, Any]] = {}
        for event in events:
            payload = json.loads(event["payload_json"])
            if event["event_type"] == "COMPONENT_CREATED":
                expected = payload.get("component")
            else:
                expected = payload.get("effective_state")
            if not isinstance(expected, dict):
                return {"valid": False, "reason": "event_missing_effective_state", "component_id": event["component_id"]}
            latest[event["component_id"]] = expected
        actual_by_id = {row["component_id"]: dict(row) for row in components}
        if set(latest) != set(actual_by_id):
            return {"valid": False, "reason": "component_event_set_mismatch"}
        for component_id, actual in actual_by_id.items():
            expected = latest[component_id]
            for field in compared_fields:
                if actual.get(field) != expected.get(field):
                    return {"valid": False, "reason": "projection_mismatch", "component_id": component_id, "field": field}
        return {"valid": True, "components_checked": len(actual_by_id), "events_checked": len(events)}

    @staticmethod
    def verify_snapshot_file(source: str | os.PathLike[str]) -> dict[str, Any]:
        """Verify the embedded SHA-256 digest of an exported snapshot file."""
        try:
            payload = json.loads(Path(source).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            return {"valid": False, "reason": "snapshot_unreadable", "detail": str(exc)}
        if not isinstance(payload, dict) or not isinstance(payload.get("snapshot_sha256"), str):
            return {"valid": False, "reason": "snapshot_digest_missing"}
        claimed_digest = payload.pop("snapshot_sha256")
        actual_digest = hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest()
        if claimed_digest != actual_digest:
            return {"valid": False, "reason": "snapshot_digest_mismatch"}
        return {"valid": True, "snapshot_sha256": claimed_digest}

    def export_snapshot(self, destination: str | os.PathLike[str]) -> dict[str, Any]:
        """Export a consistent JSON snapshot using an atomic replace."""
        with self._connection() as conn:
            conn.execute("BEGIN")
            components = [dict(r) for r in conn.execute("SELECT * FROM components ORDER BY component_id").fetchall()]
            events = conn.execute("SELECT seq,event_hash FROM events ORDER BY seq").fetchall()
            head = events[-1]["event_hash"] if events else "GENESIS"
            payload = {"schema_version": SCHEMA_VERSION, "generated_at": _now(),
                       "component_count": len(components), "components": components,
                       "event_count": len(events), "event_head_hash": head}
            payload["snapshot_sha256"] = hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest()
            conn.commit()
        path = Path(destination)
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp_name, path)
        except Exception:
            try:
                os.unlink(tmp_name)
            except FileNotFoundError:
                pass
            raise
        return payload
