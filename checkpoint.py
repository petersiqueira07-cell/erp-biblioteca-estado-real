"""Verifiable continuity checkpoints built on the existing StateLibrary MVP.

This module coordinates existing integrity/projection/snapshot checks. It does not
capture chat context automatically; callers must supply the context explicitly.
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from state_library import StateLibrary

MANIFEST_SCHEMA_VERSION = 1
MANIFEST_NAME = "manifest.json"
SNAPSHOT_NAME = "snapshot.json"
RESUME_NAME = "resume.json"


class CheckpointError(ValueError):
    """Raised when a checkpoint cannot be safely created or verified."""


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _digest_json(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _atomic_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CheckpointError(f"artefato_json_ilegivel:{path.name}") from exc
    if not isinstance(value, dict):
        raise CheckpointError(f"artefato_json_formato_invalido:{path.name}")
    return value


def _manifest_digest(manifest: Mapping[str, Any]) -> str:
    unsigned = dict(manifest)
    unsigned.pop("manifest_sha256", None)
    return _digest_json(unsigned)


def save_checkpoint(
    library: StateLibrary,
    destination: str | os.PathLike[str],
    *,
    project_id: str,
    source_commit: str,
    context: Mapping[str, Any],
    decisions: list[Mapping[str, Any]] | None = None,
    pending_items: list[Mapping[str, Any]] | None = None,
    next_step: str,
    checkpoint_id: str | None = None,
) -> dict[str, Any]:
    """Persist and verify a checkpoint; fail closed on any failed check.

    destination must be a directory that does not already exist. The supplied
    context is explicit caller input, not an automatically captured chat log.
    """
    if not isinstance(library, StateLibrary):
        raise CheckpointError("library_deve_ser_StateLibrary")
    if not isinstance(project_id, str) or not project_id.strip():
        raise CheckpointError("project_id_obrigatorio")
    if not isinstance(source_commit, str) or not source_commit.strip():
        raise CheckpointError("source_commit_obrigatorio")
    if not isinstance(context, Mapping):
        raise CheckpointError("contexto_deve_ser_mapeamento")
    if not isinstance(next_step, str) or not next_step.strip():
        raise CheckpointError("next_step_obrigatorio")
    checkpoint_id = checkpoint_id or str(uuid.uuid4())
    if not isinstance(checkpoint_id, str) or not checkpoint_id.strip() or any(
        ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-" for ch in checkpoint_id
    ):
        raise CheckpointError("checkpoint_id_invalido")

    root = Path(destination).expanduser()
    if root.exists():
        raise CheckpointError("destino_ja_existe; checkpoint_nao_sobrescrito")

    try:
        context_copy = json.loads(_canonical(dict(context)))
        decisions_copy = json.loads(_canonical(decisions or []))
        pending_copy = json.loads(_canonical(pending_items or []))
    except (TypeError, ValueError) as exc:
        raise CheckpointError("contexto_ou_listas_nao_serializaveis_em_json") from exc

    integrity = library.verify_integrity()
    projection = library.verify_projection_consistency()
    checks = {
        "event_integrity": integrity,
        "projection_consistency": projection,
    }
    if not integrity.get("valid") or not projection.get("valid"):
        return {
            "status": "BLOQUEADO",
            "checkpoint_id": checkpoint_id,
            "checks": checks,
            "reason": "estado_atual_inconsistente; nenhum_checkpoint_validado_foi_criado",
        }

    # Refuse existing paths and do not clobber any previous checkpoint.
    root.mkdir(parents=True, exist_ok=False)
    snapshot_path = root / SNAPSHOT_NAME
    manifest_path = root / MANIFEST_NAME
    resume_path = root / RESUME_NAME
    try:
        snapshot = library.export_snapshot(snapshot_path)
        snapshot_check = StateLibrary.verify_snapshot_file(snapshot_path)
        snapshot_readback = _read_json(snapshot_path)
        snapshot_bytes_sha256 = _sha256_bytes(snapshot_path.read_bytes())
        checks["snapshot_digest"] = snapshot_check
        checks["snapshot_readback"] = {
            "valid": snapshot_readback.get("snapshot_sha256") == snapshot.get("snapshot_sha256"),
            "component_count": snapshot_readback.get("component_count"),
            "event_count": snapshot_readback.get("event_count"),
        }
        if not snapshot_check.get("valid") or not checks["snapshot_readback"]["valid"]:
            checks["snapshot_readback"]["valid"] = False
            status = "SALVO_MAS_NAO_VALIDADO"
        else:
            status = "CHECKPOINT_VALIDADO"

        manifest: dict[str, Any] = {
            "manifest_schema_version": MANIFEST_SCHEMA_VERSION,
            "checkpoint_id": checkpoint_id,
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "project_id": project_id.strip(),
            "source_commit": source_commit.strip(),
            "status": status,
            "artifacts": {
                "snapshot_path": SNAPSHOT_NAME,
                "snapshot_file_sha256": snapshot_bytes_sha256,
                "snapshot_embedded_sha256": snapshot.get("snapshot_sha256"),
                "event_head_hash": snapshot.get("event_head_hash"),
                "component_count": snapshot.get("component_count"),
                "event_count": snapshot.get("event_count"),
            },
            "context_sha256": _digest_json(context_copy),
            "context": context_copy,
            "decisions": decisions_copy,
            "pending_items": pending_copy,
            "next_step": next_step.strip(),
            "checks": checks,
            "limitations": [
                "contexto fornecido explicitamente pelo chamador; nao capturado automaticamente do chat",
                "digest SHA-256 detecta alteracao, mas nao e assinatura externa",
                "checkpoint nao substitui backup/restauracao da base SQLite",
            ],
        }
        manifest["manifest_sha256"] = _manifest_digest(manifest)
        _atomic_json(manifest_path, manifest)

        manifest_readback = _read_json(manifest_path)
        manifest_valid = (
            manifest_readback.get("manifest_sha256") == _manifest_digest(manifest_readback)
            and manifest_readback.get("checkpoint_id") == checkpoint_id
        )
        resume = {
            "resume_schema_version": 1,
            "checkpoint_id": checkpoint_id,
            "project_id": project_id.strip(),
            "status": status if manifest_valid else "SALVO_MAS_NAO_VALIDADO",
            "manifest_path": MANIFEST_NAME,
            "manifest_sha256": manifest_readback.get("manifest_sha256"),
            "source_commit": source_commit.strip(),
            "next_step": next_step.strip(),
            "instruction": "Reabra este pacote e execute verify_checkpoint antes de continuar.",
        }
        _atomic_json(resume_path, resume)
        verified = verify_checkpoint(root)
        if not manifest_valid or verified.get("status") != "CHECKPOINT_VALIDADO":
            return {
                "status": "SALVO_MAS_NAO_VALIDADO",
                "checkpoint_id": checkpoint_id,
                "path": str(root),
                "checks": checks,
                "manifest_valid": manifest_valid,
                "verification": verified,
            }
        return {
            "status": "CHECKPOINT_VALIDADO",
            "checkpoint_id": checkpoint_id,
            "path": str(root),
            "manifest_sha256": manifest["manifest_sha256"],
            "snapshot_sha256": snapshot.get("snapshot_sha256"),
            "checks": checks,
            "verification": verified,
        }
    except Exception as exc:
        # Artifacts may exist for diagnosis, but they are never reported as validated.
        return {
            "status": "SALVO_MAS_NAO_VALIDADO",
            "checkpoint_id": checkpoint_id,
            "path": str(root),
            "reason": f"verification_or_persistence_error:{type(exc).__name__}",
            "detail": str(exc),
        }


def verify_checkpoint(directory: str | os.PathLike[str]) -> dict[str, Any]:
    """Reopen and verify manifest, resume package, and snapshot from disk."""
    root = Path(directory).expanduser()
    try:
        manifest = _read_json(root / MANIFEST_NAME)
        resume = _read_json(root / RESUME_NAME)
        snapshot_path = root / SNAPSHOT_NAME
        snapshot = _read_json(snapshot_path)
    except CheckpointError as exc:
        return {"status": "SALVO_MAS_NAO_VALIDADO", "valid": False, "reason": str(exc)}

    expected_path = manifest.get("artifacts", {}).get("snapshot_path")
    if expected_path != SNAPSHOT_NAME:
        return {"status": "SALVO_MAS_NAO_VALIDADO", "valid": False, "reason": "snapshot_path_invalido"}
    if manifest.get("manifest_sha256") != _manifest_digest(manifest):
        return {"status": "SALVO_MAS_NAO_VALIDADO", "valid": False, "reason": "manifest_digest_mismatch"}
    if resume.get("checkpoint_id") != manifest.get("checkpoint_id"):
        return {"status": "SALVO_MAS_NAO_VALIDADO", "valid": False, "reason": "checkpoint_id_mismatch"}
    if resume.get("manifest_sha256") != manifest.get("manifest_sha256"):
        return {"status": "SALVO_MAS_NAO_VALIDADO", "valid": False, "reason": "resume_manifest_reference_mismatch"}

    snapshot_check = StateLibrary.verify_snapshot_file(snapshot_path)
    file_digest = _sha256_bytes(snapshot_path.read_bytes())
    checks = manifest.get("checks", {})
    all_checks_pass = all(
        isinstance(checks.get(name), dict) and checks[name].get("valid") is True
        for name in ("event_integrity", "projection_consistency", "snapshot_digest", "snapshot_readback")
    )
    valid = (
        snapshot_check.get("valid") is True
        and file_digest == manifest.get("artifacts", {}).get("snapshot_file_sha256")
        and snapshot.get("snapshot_sha256") == manifest.get("artifacts", {}).get("snapshot_embedded_sha256")
        and snapshot.get("event_head_hash") == manifest.get("artifacts", {}).get("event_head_hash")
        and _digest_json(manifest.get("context")) == manifest.get("context_sha256")
        and all_checks_pass
        and manifest.get("status") == "CHECKPOINT_VALIDADO"
        and resume.get("status") == "CHECKPOINT_VALIDADO"
    )
    return {
        "status": "CHECKPOINT_VALIDADO" if valid else "SALVO_MAS_NAO_VALIDADO",
        "valid": valid,
        "checkpoint_id": manifest.get("checkpoint_id"),
        "manifest_sha256": manifest.get("manifest_sha256"),
        "snapshot_file_sha256": file_digest,
        "snapshot_verification": snapshot_check,
        "checks": checks,
    }
