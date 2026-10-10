# Contrato Canônico de Estado — versão inicial 0.1

## 1. Escopo

O contrato registra o estado de engenharia de componentes do projeto. Ele não é o estado operacional/transacional do ERP em produção.

## 2. Identidade

- `component_id`: identidade estável, legível por máquina, única no projeto.
- `event_id`: identidade idempotente de uma operação; reutilização com conteúdo diferente é erro.
- `version`: versão monotônica do registro do componente; cada transição aceita incrementa em um.
- `source_commit`: commit exato associado à observação, quando disponível; não é substituído por um identificador de execução transitório.

## 3. Dimensões independentes

### Implementação

`PLANNED`, `IN_PROGRESS`, `IMPLEMENTED`, `BLOCKED`, `UNKNOWN`.

Transições permitidas:

- `PLANNED` → `IN_PROGRESS`, `BLOCKED`, `UNKNOWN`
- `IN_PROGRESS` → `IMPLEMENTED`, `BLOCKED`, `UNKNOWN`
- `IMPLEMENTED` → `IN_PROGRESS`, `BLOCKED`, `UNKNOWN`
- `BLOCKED` → `IN_PROGRESS`, `UNKNOWN`
- `UNKNOWN` → `PLANNED`, `IN_PROGRESS`, `BLOCKED`

### Verificação

`NOT_VERIFIED`, `RUNNING`, `PARTIALLY_VERIFIED`, `VERIFIED`, `FAILED`.

Transições permitidas:

- `NOT_VERIFIED` → `RUNNING`, `PARTIALLY_VERIFIED`, `FAILED`
- `RUNNING` → `VERIFIED`, `PARTIALLY_VERIFIED`, `FAILED`
- `PARTIALLY_VERIFIED` → `RUNNING`, `VERIFIED`, `FAILED`
- `VERIFIED` → `NOT_VERIFIED`, `RUNNING`, `FAILED`
- `FAILED` → `RUNNING`, `NOT_VERIFIED`

Para mudar para `VERIFIED`, exige-se evidência `TEST_RUN` com resultado `PASS` e commit compatível com o `source_commit`, quando este estiver definido.

### Liberação

`NOT_RELEASED`, `CANDIDATE`, `RELEASED`.

Transições permitidas:

- `NOT_RELEASED` → `CANDIDATE`
- `CANDIDATE` → `RELEASED`, `NOT_RELEASED`
- `RELEASED` → `NOT_RELEASED` (revogação/rollback registrado)

Para mudar para `RELEASED`, o estado de verificação precisa ser `VERIFIED` e deve haver evidência `RELEASE` com resultado `PASS` associada ao commit atual.

## 4. Invalidação por mudança de código

Uma mudança em `source_commit` invalida a verificação e a liberação: `verification_status` volta a `NOT_VERIFIED` e `release_status` volta a `NOT_RELEASED`. A nova versão deve ser verificada em uma operação separada.

## 5. Evidência

Cada evidência contém, no mínimo:

- `kind`
- `claim`
- `source_ref`
- `result`

E, quando aplicável:

- `commit_id`
- `environment_id`
- `observed_at`
- `validity_scope`

A evidência é imutável no MVP. Um resultado histórico não é automaticamente prova para commits posteriores.

## 6. Evento e integridade

Toda criação ou transição aceita grava um evento append-only, com estado efetivo, motivo, versões anterior/posterior, timestamp e hash encadeado ao evento anterior. Evento e atualização da projeção atual são confirmados na mesma transação SQLite.

## 7. Concorrência e idempotência

- Toda transição informa `expected_version`; divergência bloqueia a escrita.
- Repetir `event_id` com o mesmo pedido não reaplica a mudança.
- Reutilizar `event_id` com pedido diferente é conflito.

## 8. Snapshots

O snapshot exportado é uma visão consolidada derivada dos registros atuais, inclui o hash do último evento e possui digest SHA-256 próprio. A escrita do arquivo usa substituição atômica.

## 9. Incerteza

Ausência de verificação não significa falha. Estado desconhecido, não verificado, falho e bloqueado são condições distintas.

## 10. Fora do escopo inicial

Autenticação/autorização, trilha externa imutável, assinatura de checkpoint, backups, restore automatizado, migração formal de schema, CI/CD, observabilidade operacional e replay completo do log para reconstrução da projeção.
