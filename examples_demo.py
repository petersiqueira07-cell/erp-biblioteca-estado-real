"""Run a disposable end-to-end demonstration of the state library."""
from pathlib import Path
from tempfile import TemporaryDirectory
from state_library import StateLibrary

with TemporaryDirectory(prefix="erp-state-mvp-") as temp:
    root = Path(temp)
    library = StateLibrary(root / "state.sqlite3")
    component = library.create_component(
        "platform.state-library", "Biblioteca de Estado Real", source_commit="demo-commit-001",
        event_id="demo-create-001",
    )
    component = library.transition(
        component["component_id"], component["version"],
        {"implementation_status": "IN_PROGRESS"}, "Início da fatia vertical",
        event_id="demo-transition-001",
    )
    snapshot = library.export_snapshot(root / "current-state.json")
    integrity = library.verify_integrity()
    print({
        "component_id": component["component_id"],
        "implementation_status": component["implementation_status"],
        "component_version": component["version"],
        "events": integrity["events_checked"],
        "integrity_valid": integrity["valid"],
        "snapshot_sha256": snapshot["snapshot_sha256"],
    })
