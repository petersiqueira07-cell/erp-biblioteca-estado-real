"""Command-line entry point for SALVAR O TT checkpoints."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from checkpoint import CheckpointError, save_checkpoint, verify_checkpoint
from state_library import StateLibrary


def _load_json_object(path: str) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CheckpointError(f"arquivo_json_ilegivel:{path}") from exc
    if not isinstance(value, dict):
        raise CheckpointError(f"arquivo_deve_conter_objeto_json:{path}")
    return value


def _load_json_list(path: str | None) -> list[dict[str, Any]]:
    if path is None:
        return []
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CheckpointError(f"arquivo_json_ilegivel:{path}") from exc
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        raise CheckpointError(f"arquivo_deve_conter_lista_de_objetos_json:{path}")
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="salvar_tt",
        description="Cria ou verifica um checkpoint verificável da Biblioteca de Estado Real.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    save = subparsers.add_parser("save", help="criar checkpoint e pacote de retomada")
    save.add_argument("--database", required=True, help="caminho para a base SQLite existente")
    save.add_argument("--destination", required=True, help="diretório novo para os artefatos")
    save.add_argument("--project-id", required=True)
    save.add_argument("--source-commit", required=True)
    save.add_argument("--repository", required=True, help="raiz do repositório Git que contém o commit de origem")
    save.add_argument("--context-json", required=True, help="arquivo JSON com contexto explicitamente selecionado")
    save.add_argument("--next-step", required=True)
    save.add_argument("--decisions-json", help="arquivo JSON opcional com lista de decisões")
    save.add_argument("--pending-json", help="arquivo JSON opcional com lista de pendências")
    save.add_argument("--checkpoint-id", help="ID estável opcional")

    verify = subparsers.add_parser("verify", help="verificar checkpoint persistido")
    verify.add_argument("--directory", required=True, help="diretório do checkpoint")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "verify":
            result = verify_checkpoint(args.directory)
            print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
            return 0 if result.get("status") == "CHECKPOINT_VALIDADO" else 2

        database_path = Path(args.database).expanduser()
        if not database_path.exists():
            raise CheckpointError("base_sqlite_inexistente; salvamento_bloqueado_para_evitar_criar_base_vazia")
        if not database_path.is_file():
            raise CheckpointError("caminho_da_base_nao_e_arquivo")
        try:
            with database_path.open("rb") as database_file:
                sqlite_header = database_file.read(16)
        except OSError as exc:
            raise CheckpointError("base_sqlite_ilegivel") from exc
        if sqlite_header != b"SQLite format 3\x00":
            raise CheckpointError("arquivo_nao_tem_cabecalho_sqlite_valido")

        source_commit = args.source_commit.strip()
        if not re.fullmatch(r"[0-9a-fA-F]{40}", source_commit):
            raise CheckpointError("source_commit_deve_ser_sha_git_completo_de_40_caracteres")
        repository_path = Path(args.repository).expanduser()
        if not repository_path.is_dir():
            raise CheckpointError("repositorio_git_inexistente")
        try:
            commit_check = subprocess.run(
                ["git", "-C", str(repository_path), "cat-file", "-e", f"{source_commit}^{{commit}}"],
                capture_output=True, text=True, timeout=10, check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise CheckpointError("nao_foi_possivel_verificar_commit_no_repositorio") from exc
        if commit_check.returncode != 0:
            raise CheckpointError("source_commit_nao_encontrado_no_repositorio_informado")

        context = _load_json_object(args.context_json)
        decisions = _load_json_list(args.decisions_json)
        pending = _load_json_list(args.pending_json)
        library = StateLibrary(database_path)
        result = save_checkpoint(
            library,
            args.destination,
            project_id=args.project_id,
            source_commit=args.source_commit,
            context=context,
            decisions=decisions,
            pending_items=pending,
            next_step=args.next_step,
            checkpoint_id=args.checkpoint_id,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        status = result.get("status")
        if status == "CHECKPOINT_VALIDADO":
            return 0
        if status == "BLOQUEADO":
            return 3
        return 2
    except CheckpointError as exc:
        print(json.dumps({"status": "BLOQUEADO", "reason": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 3
    except Exception as exc:
        print(json.dumps({
            "status": "SALVO_MAS_NAO_VALIDADO",
            "reason": f"unexpected_error:{type(exc).__name__}",
            "detail": str(exc),
        }, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
