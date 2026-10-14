# Contrato do incremento SALVAR O TT — v0.1

**Estado:** proposta de contrato para a branch `feat/salvar-tt-checkpoint`.
**Base:** Biblioteca de Estado Real — MVP 0.1.
**Método:** B15 v6.3.1 HIGH PERFORMANCE SOFTWARE ENGINEERING HARDENED permanece obrigatório e não é alterado por este incremento.

## 1. Objetivo e limites

Coordenar os mecanismos existentes da biblioteca para produzir um checkpoint verificável e um pacote explícito de retomada. O comando não presume acesso automático ao contexto de uma conversa; o chamador deve fornecer o contexto que deseja persistir.

O checkpoint descreve o estado de engenharia persistido e o contexto de continuidade fornecido. Não prova a verdade de alegações externas nem substitui backup operacional, assinatura externa ou controle de acesso.

## 2. Fluxo obrigatório

1. Validar entradas obrigatórias: diretório de destino, identificador do projeto, commit de origem e contexto explícito. Na CLI, exigir uma base SQLite existente com cabeçalho válido e `--repository` apontando para o repositório Git; validar SHA completo e existência do commit nesse repositório.
2. Executar `verify_integrity()` e `verify_projection_consistency()`.
3. Exportar snapshot usando `export_snapshot()`.
4. Verificar o snapshot com `verify_snapshot_file()` e relê-lo do disco.
5. Gerar manifesto versionado que referencie snapshot, commit, contexto, verificações e pendências.
6. Escrever manifesto atomicamente e verificá-lo após a escrita.
7. Produzir pacote de retomada com IDs e instruções.
8. Só emitir `CHECKPOINT_VALIDADO` se todas as verificações obrigatórias passarem e o snapshot relido corresponder ao manifesto.

A validação deve falhar fechada: falha ou exceção em verificação não pode gerar status validado. Artefatos parciais podem permanecer para diagnóstico, mas não devem ser rotulados como validados.

## 3. Estados de resultado

- `CHECKPOINT_VALIDADO`: persistência, verificações e leitura posterior concluídas com sucesso.
- `SALVO_MAS_NAO_VALIDADO`: há artefatos persistidos, mas alguma verificação falhou ou não pôde ser concluída.
- `BLOQUEADO`: entradas obrigatórias inválidas ou pré-condições ausentes; não iniciar salvamento.

## 4. Manifesto

O manifesto deve incluir, no mínimo:
- `manifest_schema_version`, `checkpoint_id`, `created_at_utc`;
- `project_id`, `source_commit`;
- caminho relativo e SHA-256 do snapshot, digest interno do snapshot e cabeça do histórico;
- digest do contexto explicitamente fornecido;
- resultados detalhados das verificações;
- decisões, pendências e próximo passo fornecidos pelo chamador;
- status final e limitações.

O digest externo deve cobrir o manifesto canônico excluindo o próprio campo `manifest_sha256`. O pacote deve evitar caminhos absolutos e conter apenas caminhos relativos dentro do diretório do checkpoint.

## 5. Consistência e fontes

O histórico de eventos, a projeção e o snapshot são confrontados tecnicamente. O contexto conversacional é entrada explícita e não é automaticamente reconciliado semanticamente com todas as fontes. Divergências semânticas precisam ser registradas como pendências; não devem ser resolvidas por recência presumida.

## 6. Segurança e atomicidade

- Não modificar o schema nem a lógica da biblioteca existente nesta fatia.
- Não alterar nem reescrever o B15.
- Usar escrita temporária + flush/fsync + replace atômico para manifesto e pacote.
- Nunca sobrescrever artefatos de checkpoint existentes com o mesmo ID.
- Não incluir credenciais, segredos ou dados operacionais sensíveis no contexto.
- Um digest SHA-256 detecta alteração do conteúdo coberto; não é assinatura nem prova de autenticidade externa.
- O pacote é um mecanismo de continuidade, não substitui backup/restauração da base SQLite.

## 7. Critérios de aceitação

1. Entradas incompletas bloqueiam antes de gravar.
2. Integridade inválida ou projeção inconsistente nunca produz status validado.
3. Snapshot é exportado, relido e verificado por digest.
4. Manifesto e pacote são reabertos e verificados após a escrita.
5. Alteração de conteúdo do snapshot, manifesto ou pacote é detectada.
6. Identificador já existente não é silenciosamente sobrescrito.
7. Regressão da suíte atual permanece aprovada.
8. Relatório distingue testes realmente executados de registros históricos.

## 8. Limite de integração

A API Python (`save_checkpoint` / `verify_checkpoint`) continua explícita. A proteção de caminho e a validação de proveniência descritas acima aplicam-se à CLI; a API não consegue confirmar a existência do commit sem integração explícita com o repositório. O acionamento conversacional requer um adaptador/integrador real, fora do escopo desta fatia.
