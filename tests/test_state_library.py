import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from state_library import (
    EvidenceRequired, IdempotencyConflict, InvalidTransition, StateLibrary,
    VersionConflict, StateLibraryError,
)


class StateLibraryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.db = self.root / "state.sqlite3"
        self.lib = StateLibrary(self.db)

    def tearDown(self):
        self.temp.cleanup()

    def create(self, commit="abc123", event_id="create-1"):
        return self.lib.create_component("finance.payables", "Contas a pagar", source_commit=commit, event_id=event_id)

    def test_create_event_is_idempotent(self):
        first = self.create(event_id="create-repeat")
        replay = self.lib.create_component("finance.payables", "Contas a pagar", source_commit="abc123", event_id="create-repeat")
        self.assertEqual(first["component_id"], replay["component_id"])
        self.assertEqual(len(self.lib.list_events()), 1)
        with self.assertRaises(IdempotencyConflict):
            self.lib.create_component("finance.payables", "Nome diferente", source_commit="abc123", event_id="create-repeat")

    def test_create_and_reopen_persist_state(self):
        created = self.create()
        self.assertEqual(created["implementation_status"], "PLANNED")
        self.assertEqual(created["verification_status"], "NOT_VERIFIED")
        reopened = StateLibrary(self.db).get_component("finance.payables")
        self.assertEqual(reopened["version"], 1)
        self.assertEqual(reopened["source_commit"], "abc123")

    def test_valid_transition_appends_event_and_updates_projection(self):
        self.create()
        updated = self.lib.transition("finance.payables", 1, {"implementation_status": "IN_PROGRESS"},
                                      "Development started", event_id="start-1")
        self.assertEqual(updated["implementation_status"], "IN_PROGRESS")
        self.assertEqual(updated["version"], 2)
        self.assertEqual(len(self.lib.list_events()), 2)
        self.assertTrue(self.lib.verify_integrity()["valid"])

    def test_forbidden_transition_is_rejected_without_state_change(self):
        self.create()
        with self.assertRaises(InvalidTransition):
            self.lib.transition("finance.payables", 1, {"implementation_status": "RELEASED"},
                                "Invalid state", event_id="bad-1")
        self.assertEqual(self.lib.get_component("finance.payables")["version"], 1)
        self.assertEqual(len(self.lib.list_events()), 1)

    def test_optimistic_version_conflict(self):
        self.create()
        self.lib.transition("finance.payables", 1, {"implementation_status": "IN_PROGRESS"},
                            "Start", event_id="start-1")
        with self.assertRaises(VersionConflict):
            self.lib.transition("finance.payables", 1, {"implementation_status": "BLOCKED"},
                                "Stale writer", event_id="stale-1")

    def test_same_event_is_idempotent_and_different_payload_conflicts(self):
        self.create()
        first = self.lib.transition("finance.payables", 1, {"implementation_status": "IN_PROGRESS"},
                                    "Start", event_id="same-id")
        replay = self.lib.transition("finance.payables", 1, {"implementation_status": "IN_PROGRESS"},
                                     "Start", event_id="same-id")
        self.assertEqual(first["version"], replay["version"])
        self.assertEqual(len(self.lib.list_events()), 2)
        with self.assertRaises(IdempotencyConflict):
            self.lib.transition("finance.payables", 1, {"implementation_status": "BLOCKED"},
                                "Different request", event_id="same-id")

    def test_concurrent_writers_do_not_silently_overwrite_each_other(self):
        self.create()
        def write(status, event_id):
            return self.lib.transition("finance.payables", 1, {"implementation_status": status},
                                       "Concurrent writer", event_id=event_id)
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(write, "IN_PROGRESS", "race-a"),
                       pool.submit(write, "BLOCKED", "race-b")]
        outcomes = []
        for future in futures:
            try:
                outcomes.append(("ok", future.result()))
            except (VersionConflict, StateLibraryError) as exc:
                outcomes.append(("conflict", str(exc)))
        self.assertEqual(sum(1 for kind, _ in outcomes if kind == "ok"), 1)
        self.assertEqual(self.lib.get_component("finance.payables")["version"], 2)
        self.assertEqual(len(self.lib.list_events()), 2)

    def test_verified_requires_passing_test_evidence_for_same_commit(self):
        self.create(commit="abc123")
        self.lib.transition("finance.payables", 1, {"implementation_status": "IN_PROGRESS"}, "Start", event_id="start")
        self.lib.transition("finance.payables", 2, {"implementation_status": "IMPLEMENTED"}, "Code done", event_id="done")
        self.lib.transition("finance.payables", 3, {"verification_status": "RUNNING"}, "Tests start", event_id="test-start")
        with self.assertRaises(EvidenceRequired):
            self.lib.transition("finance.payables", 4, {"verification_status": "VERIFIED"}, "Claim pass", event_id="no-evidence")
        evidence = {"kind": "TEST_RUN", "claim": "Unit suite passed", "source_ref": "tests/report.xml",
                    "commit_id": "abc123", "environment_id": "python-3.13", "result": "PASS",
                    "validity_scope": {"suite": "unit"}}
        verified = self.lib.transition("finance.payables", 4, {"verification_status": "VERIFIED"},
                                       "Test suite passed", event_id="verified", evidence=evidence)
        self.assertEqual(verified["verification_status"], "VERIFIED")
        self.assertEqual(len(self.lib.list_evidence()), 1)

    def test_source_commit_change_invalidates_verification_and_release(self):
        self.create()
        self.lib.transition("finance.payables", 1, {"implementation_status": "IN_PROGRESS"}, "Start", event_id="start")
        changed = self.lib.transition("finance.payables", 2, {"source_commit": "def456"}, "New code version", event_id="commit-change")
        self.assertEqual(changed["verification_status"], "NOT_VERIFIED")
        self.assertEqual(changed["release_status"], "NOT_RELEASED")

    def test_release_requires_verified_state_and_release_evidence(self):
        self.create(commit="abc123")
        self.lib.transition("finance.payables", 1, {"implementation_status": "IN_PROGRESS"}, "Start", event_id="r-start")
        self.lib.transition("finance.payables", 2, {"implementation_status": "IMPLEMENTED"}, "Code done", event_id="r-done")
        self.lib.transition("finance.payables", 3, {"verification_status": "RUNNING"}, "Tests start", event_id="r-test-start")
        test_evidence = {"kind": "TEST_RUN", "claim": "Tests passed", "source_ref": "report.xml", "commit_id": "abc123", "result": "PASS"}
        self.lib.transition("finance.payables", 4, {"verification_status": "VERIFIED"}, "Tests passed", event_id="r-verified", evidence=test_evidence)
        self.lib.transition("finance.payables", 5, {"release_status": "CANDIDATE"}, "Candidate prepared", event_id="r-candidate")
        release_evidence = {"kind": "RELEASE", "claim": "Release approved", "source_ref": "release-record/1", "commit_id": "abc123", "result": "PASS"}
        released = self.lib.transition("finance.payables", 6, {"release_status": "RELEASED"}, "Release recorded", event_id="r-release", evidence=release_evidence)
        self.assertEqual(released["release_status"], "RELEASED")
        self.assertEqual(len(self.lib.list_evidence()), 2)

    def test_snapshot_is_valid_json_and_has_digest(self):
        self.create()
        target = self.root / "exports" / "snapshot.json"
        snapshot = self.lib.export_snapshot(target)
        loaded = json.loads(target.read_text(encoding="utf-8"))
        self.assertEqual(loaded["component_count"], 1)
        self.assertEqual(loaded["snapshot_sha256"], snapshot["snapshot_sha256"])
        self.assertEqual(loaded["event_count"], 1)

    def test_event_and_evidence_are_immutable_at_database_layer(self):
        self.create()
        with sqlite3.connect(self.db) as conn:
            with self.assertRaises(sqlite3.IntegrityError):
                conn.execute("UPDATE events SET event_type='ALTERED' WHERE event_id='create-1'")
        conn.close()

    def test_reopen_after_abrupt_process_exit_rolls_back_uncommitted_write(self):
        self.create()
        code = r"""
import os, sqlite3, sys
conn = sqlite3.connect(sys.argv[1], isolation_level=None)
conn.execute("PRAGMA journal_mode=WAL")
conn.execute("BEGIN IMMEDIATE")
conn.execute("UPDATE components SET implementation_status='IN_PROGRESS', version=2 WHERE component_id='finance.payables'")
os._exit(71)
"""
        result = subprocess.run([sys.executable, "-c", code, str(self.db)], check=False)
        self.assertEqual(result.returncode, 71)
        reopened = StateLibrary(self.db)
        component = reopened.get_component("finance.payables")
        self.assertEqual(component["implementation_status"], "PLANNED")
        self.assertEqual(component["version"], 1)
        self.assertEqual(len(reopened.list_events()), 1)
        self.assertTrue(reopened.verify_integrity()["valid"])

    def test_failed_transition_rolls_back_projection_and_event(self):
        self.create()
        with patch.object(self.lib, "_append_event", side_effect=RuntimeError("simulated interruption")):
            with self.assertRaisesRegex(RuntimeError, "simulated interruption"):
                self.lib.transition("finance.payables", 1, {"implementation_status": "IN_PROGRESS"},
                                    "Fault injection", event_id="fault-1")
        self.assertEqual(self.lib.get_component("finance.payables")["version"], 1)
        self.assertEqual(self.lib.get_component("finance.payables")["implementation_status"], "PLANNED")
        self.assertEqual([event["event_id"] for event in self.lib.list_events()], ["create-1"])
        self.assertTrue(self.lib.verify_integrity()["valid"])

    def test_projection_consistency_passes_then_detects_divergence(self):
        self.create()
        self.lib.transition("finance.payables", 1, {"implementation_status": "IN_PROGRESS"},
                            "Start", event_id="projection-start")
        self.assertTrue(self.lib.verify_projection_consistency()["valid"])
        with sqlite3.connect(self.db) as conn:
            conn.execute("DROP TRIGGER IF EXISTS events_no_update")
            row = conn.execute("SELECT payload_json FROM events WHERE event_id='projection-start'").fetchone()
            payload = json.loads(row[0])
            payload["effective_state"]["implementation_status"] = "BLOCKED"
            conn.execute("UPDATE events SET payload_json=? WHERE event_id='projection-start'", (json.dumps(payload),))
        conn.close()
        result = self.lib.verify_projection_consistency()
        self.assertFalse(result["valid"])
        self.assertEqual(result["reason"], "projection_mismatch")

    def test_snapshot_verifier_detects_content_tampering(self):
        self.create()
        target = self.root / "snapshot.json"
        self.lib.export_snapshot(target)
        self.assertTrue(StateLibrary.verify_snapshot_file(target)["valid"])
        payload = json.loads(target.read_text(encoding="utf-8"))
        payload["components"][0]["name"] = "Tampered"
        target.write_text(json.dumps(payload), encoding="utf-8")
        result = StateLibrary.verify_snapshot_file(target)
        self.assertFalse(result["valid"])
        self.assertEqual(result["reason"], "snapshot_digest_mismatch")

    def test_integrity_verifier_detects_tampering(self):
        self.create()
        # Deliberately bypass the guard in a disposable test database to simulate corruption.
        with sqlite3.connect(self.db) as conn:
            conn.execute("DROP TRIGGER events_no_update")
            conn.execute("UPDATE events SET payload_json='{}' WHERE event_id='create-1'")
        conn.close()
        result = self.lib.verify_integrity()
        self.assertFalse(result["valid"])
        self.assertEqual(result["reason"], "event_hash_mismatch")


if __name__ == "__main__":
    unittest.main(verbosity=2)

