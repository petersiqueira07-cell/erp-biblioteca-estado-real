# Biblioteca de Estado Real — MVP 0.1

**Status:** implementação inicial experimental; não aprovada para produção.

## Objetivo

Demonstrar um fluxo vertical mínimo para registrar componentes, aplicar transições controladas, anexar evidências, preservar eventos e exportar snapshots do estado atual.

## Compatibilidade verificada neste ambiente de construção

- Python 3.13.5 disponível no ambiente de execução usado para construir/testar este artefato.
- Dependências externas: nenhuma; usa a biblioteca padrão do Python.
- Banco: SQLite, com transações, chaves estrangeiras e journal WAL.
- Isso **não** comprova que Python esteja instalado na máquina Windows auditada do usuário. O baseline dessa máquina deixou essa capacidade como não verificada.

## Conteúdo

## Documentação de referência

- [Dossiê de Continuidade do Projeto](docs/CONTINUIDADE.md) — contexto de retomada, marcos, decisões e instruções para continuar o trabalho em outra conversa.
- [Documento de Referência Auditado](docs/REFERENCIA_AUDITADA.md) — funcionamento, contrato, critérios de aceitação, cobertura de testes e limites técnicos.
- [Marco estável — validação inicial](docs/MILESTONE_VALIDACAO_INICIAL.md) — registro documental das evidências de validação.


- `state_library.py`: implementação SQLite, verificação de consistência entre eventos e projeção, e verificação do digest de snapshots.
- `tests/test_state_library.py`: testes automatizados do contrato inicial.
- `docs/STATE_CONTRACT.md`: contrato de estado e critérios de evidência.

## Executar testes

Na raiz desta pasta:

```bash
python -m unittest discover -s tests -v
```

## Uso mínimo

```python
from state_library import StateLibrary

library = StateLibrary("data/project-state.sqlite3")
component = library.create_component(
    component_id="finance.payables",
    name="Contas a pagar",
    source_commit="<commit-real-do-repositorio>",
)

library.transition(
    component_id="finance.payables",
    expected_version=component["version"],
    changes={"implementation_status": "IN_PROGRESS"},
    reason="Início da implementação",
    event_id="<id-estavel-da-operacao>",
)

library.export_snapshot("project-state/current-state.json")
print(library.verify_integrity())
```

Nunca use placeholders como evidência de um commit real. O `source_commit` deve apontar para a versão efetivamente inspecionada.

## Garantias pretendidas pelo MVP

- Atualização do estado e registro do evento dentro de uma transação SQLite.
- Controle otimista de versão (`expected_version`).
- Repetição segura de um `event_id` com conteúdo idêntico; conteúdo divergente é recusado.
- Eventos e evidências protegidos contra UPDATE/DELETE pela camada SQLite.
- Cadeia SHA-256 de eventos verificável.
- Evidência de teste aprovada e associada ao commit exigida para marcar `VERIFIED`.
- Alteração de commit invalida verificação e liberação automaticamente.
- Snapshot JSON escrito por substituição atômica, com verificador do digest SHA-256.
- Verificação explícita de consistência entre o último evento de cada componente e o estado consolidado atual.

## Última validação local

A suíte local contém 17 testes automatizados, incluindo falha injetada antes do commit, encerramento abrupto de um processo com transação aberta, concorrência, consistência da projeção e adulteração do snapshot. Consulte o resultado da execução associado à entrega; esses testes não equivalem a uma auditoria de produção.

## Limitações conhecidas

- O MVP ainda não implementa autenticação, autorização multiusuário, assinatura criptográfica externa, replicação, backup/restore automatizado, migrações de schema, integração CI/CD nem reconstrução integral do estado apenas pelo replay do log.
- A cadeia SHA-256 detecta alterações na sequência, mas não impede um atacante com acesso ao arquivo de banco de modificar também os hashes; produção exigiria proteção externa do checkpoint/assinatura e controles de acesso.
- O MVP não é o banco transacional do ERP e não deve armazenar dados financeiros ou pessoais de produção.
- `VERIFIED` significa que a biblioteca recebeu evidência declarada compatível com o contrato; ainda não valida por conta própria a veracidade externa do relatório referenciado.
- A semântica de estado, transições e release precisa de revisão de domínio antes de ser tratada como contrato definitivo.
