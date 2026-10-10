# Marco estável — validação inicial do MVP

**Data:** 2026-10-10  
**Projeto:** Biblioteca de Estado Real — MVP 0.1  
**Branch:** `main`  
**Commit validado:** `4e52ee8e265525f407c201cd6085accd644810d4`

## Evidências registradas

- Suíte local: **17/17 testes aprovados**, conforme execução registrada durante a sessão de desenvolvimento.
- GitHub Actions: jobs **Python 3.13 / unittest** e **Python 3.14 / unittest** concluídos com sucesso.
- Execução CI: https://github.com/petersiqueira07-cell/erp-biblioteca-estado-real/actions/runs/38083506942
- Workflow: [tests.yml](../.github/workflows/tests.yml)

## Decisão

**Marco de validação inicial concluído.** O commit acima é o ponto de referência para o estado testado do MVP e do workflow de CI.

Este registro é documental: não altera o comportamento do software nem cria uma garantia além das evidências listadas. Os avisos de depreciação das actions/runtime e da migração futura de `ubuntu-latest` permanecem conhecidos e não bloquearam essa execução.

## Limites

A aprovação comprova somente que a suíte automatizada existente passou nas versões de Python listadas. Não constitui auditoria de segurança, certificação, aprovação para produção nem validação de requisitos de domínio.

As limitações descritas no [README](../README.md) e no [contrato de estado](STATE_CONTRACT.md) permanecem vigentes. Não foram acrescentadas funcionalidades nem testes nesta etapa.
