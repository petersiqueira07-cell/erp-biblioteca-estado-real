# Dossiê de Continuidade — Biblioteca de Estado Real

**Consolidado em:** 2026-10-10  
**Projeto:** Biblioteca de Estado Real — MVP 0.1  
**Repositório:** https://github.com/petersiqueira07-cell/erp-biblioteca-estado-real  
**Branch de referência:** `main`  
**Status:** MVP experimental; não aprovado para produção.

## 1. Como retomar em outra conversa

Anexe este documento e use a instrução abaixo:

> Vamos continuar o projeto Biblioteca de Estado Real — MVP 0.1. Leia o Dossiê de Continuidade anexado e confira as referências canônicas quando necessário. O B15 v6.3.1 HIGH PERFORMANCE SOFTWARE ENGINEERING HARDENED é o método operacional obrigatório; não o reescreva. Trabalhe com rigor: não confunda intenção, plano, execução, observação, verificação e aprovação. Preserve os marcos registrados, não invente evidências e não crie burocracia adicional sem ganho material. Antes de alterar código, identifique a menor ação suficiente para o objetivo e confirme que está autorizada. O projeto permanece experimental e não aprovado para produção. Primeiro, resuma o estado confirmado e avance somente na tarefa que eu indicar.

## 2. Propósito e limites

A biblioteca Python registra estados de engenharia de componentes usando SQLite e histórico de eventos. Mantém dimensões independentes de implementação, verificação e liberação. Não é um ERP operacional, não substitui o banco transacional do ERP e não deve armazenar dados financeiros ou pessoais de produção.

Capacidades implementadas no MVP:
- Registro e consulta de componentes.
- Transições controladas e controle otimista por `expected_version`.
- Idempotência por `event_id`; pedidos divergentes com o mesmo ID são recusados.
- Atualização do estado e registro do evento na mesma transação SQLite.
- Evidências declaradas para verificação/liberação.
- Invalidação da verificação e liberação quando `source_commit` muda.
- Triggers contra UPDATE/DELETE comuns em eventos e evidências.
- Verificação da cadeia SHA-256, consistência da projeção e snapshots JSON com digest.

Limites essenciais:
- Sem autenticação/autorização multiusuário.
- Evidência registrada não prova a verdade de uma fonte externa.
- Acesso direto ao arquivo SQLite pode contornar triggers e permitir alterar dados/hashes.
- O hash atual é calculado sobre `previous_hash` e `payload_json`; não autentica diretamente todas as colunas de metadados da linha de evento.
- Sem assinatura/checkpoint externo, backup/restore automatizado, migrações formais ou replay integral garantido.
- O contrato de estados e release ainda exige revisão de domínio antes de ser considerado definitivo.

## 3. Repositório e referências canônicas

- [README](../README.md)
- [Implementação](../state_library.py)
- [Contrato de estado](STATE_CONTRACT.md)
- [Testes](../tests/test_state_library.py)
- [Workflow CI](../.github/workflows/tests.yml)
- [Marco de validação inicial](MILESTONE_VALIDACAO_INICIAL.md)
- [Documento de Referência Auditado (Markdown)](REFERENCIA_AUDITADA.md)
- [Execução GitHub Actions registrada](https://github.com/petersiqueira07-cell/erp-biblioteca-estado-real/actions/runs/38083506942)

## 4. Marcos e evidências registradas

| Marco | Referência | Registro |
|---|---|---|
| Publicação inicial | `7467ede` | Histórico inicial conhecido |
| Código e CI do marco de validação | `4e52ee8e265525f407c201cd6085accd644810d4` | Commit indicado no registro do marco |
| Registro documental do marco | `3bbe72290b9e336fd67f5f9d71238f3429353278` | Inclusão de `docs/MILESTONE_VALIDACAO_INICIAL.md` |

O histórico da sessão registra 17/17 testes locais aprovados e CI bem-sucedida em Python 3.13 e 3.14. Isso é evidência histórica registrada; não afirmar que os testes foram reexecutados sem fazê-lo. Confirme a branch/commit atuais no GitHub antes de usá-los como base de novas alterações.

O marco é documental e não altera o comportamento do software. Os testes existentes não são certificação, auditoria de segurança nem aprovação para produção.

## 5. Contrato funcional resumido

- Implementação: `PLANNED`, `IN_PROGRESS`, `IMPLEMENTED`, `BLOCKED`, `UNKNOWN`.
- Verificação: `NOT_VERIFIED`, `RUNNING`, `PARTIALLY_VERIFIED`, `VERIFIED`, `FAILED`.
- Liberação: `NOT_RELEASED`, `CANDIDATE`, `RELEASED`.
- Toda transição usa `expected_version`; versão obsoleta provoca conflito.
- Repetir `event_id` com o mesmo pedido não reaplica a operação; pedido diferente gera conflito.
- `VERIFIED` exige evidência `TEST_RUN/PASS) compatível com o commit quando definido.
- `RELEASED` exige estado `VERIFIED` e evidência `RELEASE/PASS) compatível com o commit quando definido.
- Alterar `source_commit` reinicia verificação e liberação para `NOT_VERIFIED` e `NOT_RELEASED`.

## 6. Baseline técnico local

O documento de baseline anterior registrou Windows 10 Pro 64 bits, build 19045; Intel Core i5-6400; cerca de 7,89 GB de RAM visíveis; SSD de 120 GB com espaço livre limitado na coleta; WSL 2 e Docker funcionais naquela coleta. A instalação real de Python na máquina Windows **não foi comprovada**. Esse baseline descreve o momento da coleta, não garante o estado atual. O ambiente de construção/CI com Python não comprova que Python esteja disponível na máquina local.

## 7. Executar demonstração e testes

Na raiz do projeto, com Python instalado no ambiente de execução:

```bash
python examples_demo.py
python -m unittest discover -s tests -v
```

A demonstração usa diretório temporário e remove os arquivos ao terminar; não cria banco permanente de trabalho.

## 8. Regras operacionais a preservar

1. O B15 v6.3.1 é o método operacional obrigatório; não o reescrever.
2. Rigor técnico com pragmatismo: controles devem proteger o trabalho, não substituí-lo.
3. Não acrescentar ciclos de auditoria, gates, testes ou artefatos sem benefício material demonstrável.
4. Não reabrir o marco estável sem motivo material ou solicitação.
5. Não confundir documento criado com documento incorporado ao GitHub.
6. Não declarar o MVP pronto para produção.
7. Atualizar este dossiê apenas quando houver mudança material de estado, decisão ou marco; não a cada interação trivial.

## 9. Próximo estado de trabalho

Este dossiê não autoriza nova tarefa técnica automaticamente. Quando o usuário indicar a próxima tarefa, identificar o resultado concreto, consultar somente as fontes necessárias, executar a menor ação suficiente e autorizada, validar proporcionalmente ao risco e registrar o resultado quando isso fizer parte do objetivo.

**Regra final: o projeto precisa sobreviver à conversa.** Repositório, commits, marcos e documentos são a referência persistente; a memória do chat é apoio.
