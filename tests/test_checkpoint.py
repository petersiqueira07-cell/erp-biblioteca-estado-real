import json
import tempfile
import unittest
from pathlib import Path

from checkpoint import CheckpointError, save_checkpoint, verify_checkpoint
from salvar_tt import main as cli_main
from state_library import StateLibrary


class CheckpointTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.db = self.root / "state.sqlite3"
        self.library = StateLibrary(self.db)
        self.library.create_component(
            "docs.continuity",
            "Continuidade",
            source_commit="abc123",
            event_id="create-continuity",
        )

    def tearDown(self):
        self.temp.cleanup()

    def save(self, destination=None, **kwargs):
        context = kwargs.pop("context", {"last_action": "test", "facts": ["explicit input"]})
        return save_checkpoint(
            self.library,
            destination or (self.root / "checkpoint"),
            project_id="biblioteca-estado-real",
            source_commit="abc123",
            context=context,
            next_step="Review checkpoint",
            **kwargs,
        )

    def test_save_and_reopen_checkpoint(self):
        result = self.save()
        self.assertEqual(result["status"], "CHECKPOINT_VALIDADO", result)
        verification = verify_checkpoint(result["path"])
        self.assertTrue(verification["valid"], verification)

    def test_existing_destination_is_not_overwritten(self):
        destination = self.root / "checkpoint"
        destination.mkdir()
        (destination / "keep.txt").write_text("keep", encoding="utf-8")
        with self.assertRaises(CheckpointError):
            self.save(destination=destination)
        self.assertEqual((destination / "keep.txt").read_text(encoding="utf-8"), "keep")

    def test_missing_source_commit_blocks_before_writing(self):
        destination = self.root / "blocked"
        with self.assertRaises(CheckpointError):
            save_checkpoint(
                self.library, destination, project_id="p", source_commit="",
                context={}, next_step="continue",
            )
        self.assertFalse(destination.exists())

    def test_snapshot_tampering_is_detected(self):
        result = self.save()
        snapshot_path = Path(result["path"]) / "snapshot.json"
        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
        snapshot["component_count"] = 999
        snapshot_path.write_text(json.dumps(snapshot), encoding="utf-8")
        verification = verify_checkpoint(result["path"])
        self.assertFalse(verification["valid"])
        self.assertEqual(verification["status"], "SALVO_MAS_NAO_VALIDADO")

    def test_manifest_tampering_is_detected(self):
        result = self.save()
        manifest_path = Path(result["path"]) / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["next_step"] = "silently changed"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        verification = verify_checkpoint(result["path"])
        self.assertFalse(verification["valid"])

    def test_resume_reference_tampering_is_detected(self):
        result = self.save()
        resume_path = Path(result["path"]) / "resume.json"
        resume = json.loads(resume_path.read_text(encoding="utf-8"))
        resume["next_step"] = "silently changed"
        resume_path.write_text(json.dumps(resume), encoding="utf-8")
        verification = verify_checkpoint(result["path"])
        self.assertFalse(verification["valid"])

    def test_context_must_be_json_serializable(self):
        with self.assertRaises(CheckpointError):
            self.save(context={"not_json": object()})

    def test_cli_save_missing_database_blocks_without_creating_database(self):
        missing_db = self.root / "missing" / "state.sqlite3"
        context_file = self.root / "context.json"
        context_file.write_text(json.dumps({"fact": "explicit"}), encoding="utf-8")
        destination = self.root / "new-checkpoint"
        exit_code = cli_main([
            "save",
            "--database", str(missing_db),
            "--destination", str(destination),
            "--project-id", "biblioteca-estado-real",
            "--source-commit", "a" * 40,
            "--repository", str(self.root),
            "--context-json", str(context_file),
            "--next-step", "continue",
        ])
        self.assertEqual(exit_code, 3)
        self.assertFalse(missing_db.exists())
        self.assertFalse(missing_db.parent.exists())
        self.assertFalse(destination.exists())

    def test_cli_save_rejects_non_sqlite_file(self):
        invalid_db = self.root / "not-sqlite.db"
        invalid_db.write_text("not a sqlite database", encoding="utf-8")
        context_file = self.root / "context.json"
        context_file.write_text(json.dumps({"fact": "explicit"}), encoding="utf-8")
        destination = self.root / "new-checkpoint"
        exit_code = cli_main([
            "save",
            "--database", str(invalid_db),
            "--destination", str(destination),
            "--project-id", "biblioteca-estado-real",
            "--source-commit", "a" * 40,
            "--repository", str(self.root),
            "--context-json", str(context_file),
            "--next-step", "continue",
        ])
        self.assertEqual(exit_code, 3)
        self.assertFalse(destination.exists())

    def test_cli_verify_returns_success_for_valid_checkpoint(self):
        result = self.save()
        exit_code = cli_main(["verify", "--directory", result["path"]])
        self.assertEqual(exit_code, 0)


if __name__ == "__main__":
    unittest.main()
