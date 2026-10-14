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


## Incremento SALVAR O TT — checkpoint verificável

Contrato: [docs/SALVAR_TT_CONTRACT.md](docs/SALVAR_TT_CONTRACT.md).

A primeira fatia oferece uma API Python e uma CLI explícita. Ela **não captura automaticamente uma conversa**: o operador deve preparar um arquivo JSON contendo somente o contexto autorizado a persistir.

Criar um checkpoint:

```bash
python salvar_tt.py save \
  --database data/project-state.sqlite3 \
  --destination checkpoints/tt-2026-10-12-001 \
  --project-id biblioteca-estado-real \
  --source-commit <commit-real-inspecionado> \
  --repository . \
  --context-json context.json \
  --next-step "Revisar a próxima tarefa autorizada"
```

Verificar um checkpoint já gravado:

```bash
python salvar_tt.py verify --directory checkpoints/tt-2026-10-12-001
```

A saída JSON usa os estados `CHECKPOINT_VALIDADO`, `SALVO_MAS_NAO_VALIDADO` ou `BLOQUEADO`. Código de saída: 0 para validação, 2 para persistência não validada/verificação falha e 3 para bloqueio/entrada inválida. O caminho da base deve apontar para um arquivo SQLite existente; o comando bloqueia base ausente ou arquivo sem cabeçalho SQLite. `--repository` é obrigatório: o comando exige SHA completo de 40 caracteres e confirma que o commit existe no repositório Git informado. Isso valida existência, não prova sozinho que o commit corresponde semanticamente à base. O diretório de destino deve ser novo; o comando não sobrescreve checkpoints existentes.

Arquivos gerados: `snapshot.json`, `manifest.json` e `resume.json`. A verificação confere os digests e as referências entre esses artefatos. O snapshot representa o estado técnico da base no momento da exportação; o contexto de conversa é uma entrada separada fornecida pelo operador.

**Limites:** digest não é assinatura externa; o pacote não substitui backup/restore da base; a verificação posterior do pacote confirma os artefatos gravados, não consulta automaticamente o estado vivo do banco nem confirma semanticamente fontes externas. O comando precisa ser executado no ambiente que tenha a base SQLite correta e a versão do código correspondente.

## Última validação local

A suíte local contém 17 testes automatizados, incluindo falha injetada antes do commit, encerramento abrupto de um processo com transação aberta, concorrência, consistência da projeção e adulteração do snapshot. Consulte o resultado da execução associado à entrega; esses testes não equivalem a uma auditoria de produção.

## Limitações conhecidas

- O MVP ainda não implementa autenticação, autorização multiusuário, assinatura criptográfica externa, replicação, backup/restore automatizado, migrações de schema, integração CI/CD nem reconstrução integral do estado apenas pelo replay do log.
- A cadeia SHA-256 detecta alterações na sequência, mas não impede um atacante com acesso ao arquivo de banco de modificar também os hashes; produção exigiria proteção externa do checkpoint/assinatura e controles de acesso.
- O MVP não é o banco transacional do ERP e não deve armazenar dados financeiros ou pessoais de produção.
- `VERIFIED` significa que a biblioteca recebeu evidência declarada compatível com o contrato; ainda não valida por conta própria a veracidade externa do relatório referenciado.
- A semântica de estado, transições e release precisa de revisão de domínio antes de ser tratada como contrato definitivo.
