# Documento de Referência Auditado — Biblioteca de Estado Real, MVP 0.1

**Versão documental:** 1.0  
**Data:** 2026-10-10  
**Escopo:** revisão documental e inspeção estática de `README.md`, `state_library.py`, `docs/STATE_CONTRACT.md` e `tests/test_state_library.py` consultados na branch `main`.  
**Status do produto:** MVP experimental — não aprovado para produção.

## 1. Conclusão executiva

A Biblioteca de Estado Real é uma biblioteca Python para registrar estado de engenharia de componentes de um projeto, usando SQLite e um histórico de eventos. A implementação consultada é coerente com o objetivo de manter estados, versões, motivos e evidências declaradas rastreáveis.

Não é um ERP operacional, não executa processos financeiros e não substitui o banco transacional do ERP. O MVP não deve armazenar dados financeiros ou pessoais de produção.

Esta é uma revisão documental e estática. Não constitui auditoria independente de segurança, certificação, teste de penetração nem aprovação para produção. A suíte não foi reexecutada durante a elaboração deste documento.

## 2. Arquitetura e fluxo

Uma aplicação ou operador chama a API Python. A biblioteca valida a solicitação, lê o estado no SQLite, valida versão e transição, aplica as regras de evidência e grava a atualização e o evento na mesma transação. A biblioteca não decide autonomamente que um componente está pronto.

Fluxo típico:
1. Criar componente com estado inicial.
2. Solicitar transição informando `expected_version`, mudanças, motivo e `event_id`.
3. Validar estado de destino, versão e evidências exigidas.
4. Atualizar a projeção e registrar evento na transação.
5. Consultar estado/histórico, verificar integridade ou exportar snapshot.

## 3. Estruturas persistidas

| Estrutura | Finalidade |
|---|---|
| `components` | Identidade, nome, tipo, estados, commit associado, versão e timestamps; representa o estado atual. |
| `events` | Identificador, componente, tipo, versões, payload, hashes e timestamp; registra operações aceitas. |
| `evidence` | Tipo de evidência, alegação, referência, resultado, commit, ambiente, data observada e escopo de validade. |

A inicialização usa SQLite, chaves estrangeiras, `busy_timeout` e journal WAL. O código declara `SCHEMA_VERSION = 1), mas não há migração formal de schema no MVP.

## 4. Estados e critérios

- **Implementação:** `PLANNED`, `IN_PROGRESS`, `IMPLEMENTED`, `BLOCKED`, `UNKNOWN`.
- **Verificação:** `NOT_VERIFIED`, `RUNNING`, `PARTIALLY_VERIFIED`, `VERIFIED`, `FAILED`.
- **Liberação:** `NOT_RELEASED`, `CANDIDATE`, `RELEASED`.

As transições permitidas são explicitamente mapeadas em `state_library.py` e documentadas em [STATE_CONTRACT.md](STATE_CONTRACT.md). As três dimensões são independentes: implementação concluída não implica verificação nem liberação.

Para mudar para `VERIFIED`, o código exige evidência `TEST_RUN` com resultado `PASS) e correspondência de `commit_id` com `source_commit` quando este está definido. Para mudar para `RELEASED`, o estado de verificação deve ser `VERIFIED` e deve existir evidência `RELEASE/PASS) compatível com o commit quando aplicável. Alterar `source_commit` invalida verificação e liberação.

## 5. Concorrência, idempotência e transações

- `expected_version` evita que uma escrita com versão obsoleta seja aceita silenciosamente.
- Repetir `event_id` com pedido idêntico não reaplica a operação; conteúdo divergente gera conflito.
- A projeção do componente e o evento são gravados na mesma transação SQLite.
- O código usa `BEGIN IMMEDIATE` e `busy_timeout`; existe teste de concorrência com dois escritores.
- Essas propriedades não equivalem a um serviço distribuído multiusuário ou de alta disponibilidade.

## 6. Integridade e snapshots: limites

Eventos e evidências têm triggers SQLite contra UPDATE/DELETE comuns. A cadeia SHA-256 é calculada a partir de `previous_hash` e `payload_json); os verificadores podem detectar alterações nesses dados encadeados.

**Ressalva técnica:** o hash do evento não cobre diretamente todas as colunas da linha `events`, incluindo metadados como `event_type`, `component_id`, `version_before`, `version_after` e `created_at`. Portanto, não deve ser descrito como autenticação criptográfica de todos os metadados. Um agente com acesso de escrita ao arquivo SQLite pode desativar triggers ou reconstruir hashes.

O snapshot JSON inclui dados consolidados, contagens, hash do último evento e digest SHA-256. A escrita usa arquivo temporário e substituição atômica. O digest detecta alteração em relação ao valor armazenado, mas, sem assinatura/checkpoint externo confiável, não comprova autoria nem impede que alguém altere o conteúdo e recalcule o digest.

## 7. Cobertura de testes registrada

O arquivo de testes consultado contém 17 testes cobrindo:
- criação e persistência;
- idempotência e conflitos de `event_id`;
- transições válidas e inválidas;
- conflito de versão e concorrência;
- exigência de evidência para verificação e liberação;
- invalidação por mudança de commit;
- snapshot e digest;
- triggers de imutabilidade;
- rollback após falha injetada ou saída abrupta;
- consistência da projeção e detecção de adulteração em cenários simulados.

O histórico do projeto registra 17/17 testes aprovados localmente e execução de CI em Python 3.13 e 3.14 [neste workflow](https://github.com/petersiqueira07-cell/erp-biblioteca-estado-real/actions/runs/38083506942). Esse registro histórico não significa que os testes tenham sido reexecutados durante a elaboração deste documento. Cobertura existente não é prova formal nem auditoria de produção.

## 8. Critérios de aceitação resumidos

| ID | Critério | Resultado esperado |
|---|---|---|
| CR-01 | Criação | Estado inicial, versão 1 e evento de criação. |
| CR-02 | Transição válida | Estado alterado, versão incrementada e evento registrado. |
| CR-03 | Transição inválida | Rejeição sem persistência parcial. |
| CR-04 | Concorrência | Versão obsoleta recusada. |
| CR-05 | Idempotência | Repetição idêntica não duplica; pedido diferente conflita. |
| CR-06 | Verificação | `VERIFIED` exige `TEST_RUN/PASS` e commit compatível quando definido. |
| CR-07 | Liberação | `RELEASED` exige `VERIFIED` e `RELEASE/PASS` compatível. |
| CR-08 | Mudança de commit | Verificação e liberação são invalidadas. |
| CR-09 | Integridade | Alterações simuladas nos dados encadeados são detectadas pelos verificadores previstos. |
| CR-10 | Snapshot | JSON válido; alteração sem atualização do digest é detectada. |
| CR-11 | Escopo | Não usar como banco transacional nem para dados sensíveis de produção. |

## 9. Lacunas antes de produção

| Lacuna | Consequência | Controle a avaliar antes de produção |
|---|---|---|
| Sem autenticação/autorização | Não identifica autoria nem limita permissões. | Identidade, autorização por função e trilha de acesso. |
| Banco local alterável | Controles podem ser contornados por acesso direto. | Restringir acesso e avaliar checkpoint/assinatura externa. |
| Evidência declarativa | A referência não prova autenticidade da fonte. | Pipeline confiável, assinatura e retenção de artefatos. |
| Hash não cobre todos os metadados | Algumas colunas não são diretamente autenticadas. | Canonicalizar e hashear todos os campos relevantes; testar adulteração. |
| Sem backup/restore automatizado | Risco de perda de dados. | Cópias, retenção e teste de restauração. |
| Sem migrações formais | Atualizações de schema são arriscadas. | Migrações versionadas e testes de upgrade. |
| Sem replay integral | Não há reconstrução garantida apenas pelo log. | Implementar replay versionado se for requisito. |
| Sem observabilidade operacional | Falhas podem não ser detectadas cedo. | Logging, métricas e alertas conforme necessidade. |
| Sem aprovação de domínio | Estados podem não refletir processo real. | Revisão por responsáveis de engenharia, QA, segurança e domínio. |

A lista orienta decisões proporcionais ao caso de uso; não significa que todas as melhorias sejam necessárias para uma demonstração local.

## 10. Execução publicada

Com Python instalado, na raiz do repositório:

```bash
python examples_demo.py
python -m unittest discover -s tests -v
```

A demonstração usa diretório temporário e remove os arquivos ao terminar.

## 11. Veredito

| Dimensão | Veredito |
|---|---|
| Descrição funcional | Coerente com o código consultado nos mecanismos centrais. |
| Contrato de estado | Explícito, versão inicial; sem aprovação final de domínio. |
| Testes | 17 testes identificados; úteis, mas não exaustivos. |
| Integridade criptográfica | Limitada; não equivale a assinatura de todos os metadados. |
| Segurança de produção | Não aprovada. |
| Uso recomendado | Desenvolvimento e demonstração controlada. |

A biblioteca é um registro técnico experimental útil para tornar estados e mudanças rastreáveis em condições delimitadas. O seu valor não é executar o ERP nem certificar automaticamente a qualidade do software.

## 12. Fontes primárias

- [README](../README.md)
- [Implementação](../state_library.py)
- [Contrato de estado](STATE_CONTRACT.md)
- [Testes](../tests/test_state_library.py)
- [Marco de validação inicial](MILESTONE_VALIDACAO_INICIAL.md)
- [CI registrada](https://github.com/petersiqueira07-cell/erp-biblioteca-estado-real/actions/runs/38083506942)
- [Dossiê de Continuidade](CONTINUIDADE.md)
