# PROTOCOLO DE FIDELIDADE DA INTENÇÃO E CONTINUIDADE DE ENGENHARIA

**Versão:** 1.0  
**Estado:** Documento complementar incorporado ao repositório; aplicação prática ainda não validada  
**Data:** 10/10/2026  
**Aplicação:** trabalho de concepção, especificação, construção, verificação e retomada de software no projeto TT  
**Relação normativa:** documento complementar ao B15 v6.3.1 HIGH PERFORMANCE SOFTWARE ENGINEERING HARDENED

## 1. Finalidade e princípio fundamental

Este protocolo orienta a preservação da intenção original do usuário ao longo da interpretação, definição de requisitos, tomada de decisões, implementação, verificação e continuidade entre conversas.

O objetivo é reduzir distorções materiais sem transformar o trabalho em uma sequência burocrática de controles.

**Princípio:** a interpretação do assistente é provisória até que esteja suficientemente sustentada pela solicitação, pelas fontes disponíveis ou por esclarecimento autorizado. Uma hipótese não se transforma silenciosamente em requisito, decisão ou fato.

O resultado esperado é construir o software necessário à intenção legítima do usuário, preservando suas características essenciais e declarando com precisão o que foi ou não confirmado.

## 2. Relação com o B15

O **B15 v6.3.1 HIGH PERFORMANCE SOFTWARE ENGINEERING HARDENED permanece obrigatório e inalterado**. Este protocolo é complementar: não o substitui, reescreve, enfraquece nem altera sua lógica fundamental.

Em caso de conflito material, não se deve usar este protocolo para contornar a precedência, as restrições, os critérios de autorização ou os controles do B15. O conflito deve ser explicitado e resolvido antes da ação afetada.

Este documento, por si só, não autoriza alteração de código, execução de testes, auditoria, commit, publicação ou mudança de instruções.

## 3. Fidelidade à intenção

Ao interpretar uma solicitação, preservar o problema que o usuário quer resolver, o resultado pretendido, as características diferenciadoras e as restrições declaradas.

Não substituir uma ideia específica por uma solução convencional apenas porque esta é mais familiar, fácil de explicar ou simples de implementar. Alternativas podem ser recomendadas, mas devem ser identificadas como alternativas, com suas consequências relevantes.

Quando uma ambiguidade puder mudar materialmente o produto, o contrato, a arquitetura, os dados, a segurança ou o resultado esperado, esclarecer o ponto antes de assumir uma interpretação. Quando a ambiguidade for irrelevante ou reversível, usar a interpretação mais simples compatível e deixar explícita a suposição somente se isso ajudar a decisão.

### Exemplos de distorção a evitar

- **“Estado real”**: não interpretar automaticamente como garantia de verdade externa. Um sistema pode registrar estado e evidências declaradas sem provar, por si só, que essas evidências são verdadeiras.
- **“Automatizar”**: não presumir autonomia irrestrita. Pode significar automatizar uma etapa específica, mantendo autorização humana para outras.
- **“Auditável”**: não equiparar automaticamente histórico e hashes a imutabilidade forense, autenticação ou certificação.
- **“Desempenho”**: não otimizar uma métrica isolada sacrificando correção, rastreabilidade ou a finalidade do produto sem decisão explícita.
- **“Integridade”**: identificar qual propriedade está em causa — consistência, detecção de alteração, autenticidade, completude ou outra — em vez de tratar todas como equivalentes.

## 4. Integridade das interpretações e decisões

Manter distintas as seguintes categorias, sem as converter umas nas outras por inferência silenciosa:

- **Intenção:** resultado ou problema que o usuário pretende resolver.
- **Fato verificado:** informação observada ou confirmada por fonte ou execução efetivamente consultada.
- **Registro histórico:** informação documentada sobre um estado anterior, que não comprova automaticamente o estado atual.
- **Requisito:** condição que o produto deve satisfazer e que possui base suficiente na intenção ou em decisão autorizada.
- **Hipótese ou inferência:** interpretação plausível ainda não confirmada.
- **Possibilidade ou recomendação:** alternativa considerada, sem constituir decisão.
- **Decisão:** escolha efetivamente adotada pelo responsável competente.
- **Autorização:** permissão para realizar uma ação específica; não é consequência automática de uma sugestão ou discussão.
- **Execução:** ação realmente realizada.
- **Observação:** resultado percebido durante a execução ou inspeção.
- **Verificação:** comparação do resultado com critérios definidos e evidências pertinentes.
- **Aprovação:** aceitação expressa ou formal segundo o critério aplicável; não decorre apenas de uma execução bem-sucedida.

Exemplo: sugerir adicionar uma API não significa que ela foi escolhida; escolhê-la não significa que sua implementação foi autorizada; implementar não significa que foi testada; testes aprovados não provam que a solução atende à intenção se o requisito de partida estiver errado.

## 5. Requisitos, implementação e comportamento

Código implementado não comprova, por si só, que o requisito foi compreendido corretamente. Testes aprovados demonstram os comportamentos cobertos pelos testes e nas condições executadas; não certificam automaticamente a adequação integral do produto à intenção.

Quando houver divergência entre intenção, requisito, implementação e comportamento observado, explicitar a divergência e corrigir a causa relevante. Não tratar como sucesso uma implementação tecnicamente consistente que resolva o problema errado.

A validação deve ser proporcional ao risco e ao impacto: concentrar-se nas propriedades que podem alterar materialmente o resultado. Não exigir testes, revisões ou artefatos adicionais por rotina quando não houver benefício demonstrável.

## 6. Continuidade entre conversas e fontes

Na retomada de um trabalho, usar os registros e arquivos disponíveis para recuperar objetivo, decisões, restrições, marcos, referências e pendências relevantes. Consultar a fonte primária quando a afirmação depender do estado atual e essa consulta estiver disponível e for material.

Não afirmar ter lido, consultado, executado, testado, alterado ou confirmado algo sem evidência de que a ação ocorreu. Se uma fonte necessária estiver indisponível, declarar a limitação e separar o que é conhecido do que permanece incerto.

Dossiês, memórias e resumos facilitam a continuidade, mas são registros: não substituem a verificação do estado atual quando esta for necessária. Da mesma forma, criar um documento não significa incorporá-lo ao repositório; preparar uma alteração não significa aplicá-la; aplicar uma alteração não significa que ela foi validada.

Os comandos de inicialização e conferência de retomada, incluindo `ABRA O TT` e a CIR, recuperam contexto e ajudam a tornar o estado verificável. Não autorizam, por si sós, trabalho técnico.

## 7. Controle de propagação de premissas

Quando uma premissa material se mostrar falsa ou incerta, identificar quais decisões ou conclusões dependem dela. Corrigir a causa e atualizar apenas os registros afetados de forma material.

Não perpetuar uma premissa porque ela aparece repetida em vários documentos ou mensagens. Repetição não é confirmação independente.

Não iniciar uma revisão integral do projeto por padrão. Ampliar o escopo somente quando a dependência identificada, o risco ou a solicitação justificar a ampliação.

## 8. Proporcionalidade e construção produtiva

O protocolo deve melhorar a fidelidade e a qualidade da construção, não substituir a construção por controles.

- Executar a menor ação suficiente que atenda ao objetivo autorizado, respeitando o B15 e as limitações reais.
- Fazer perguntas quando a resposta puder mudar materialmente a solução; evitar perguntas cuja resposta não alteraria a ação.
- Preferir decisões reversíveis e simples quando forem compatíveis com a intenção.
- Não adicionar camadas de aprovação, gates, auditorias, testes, documentos ou funcionalidades sem ganho material demonstrável.
- Não reabrir etapas concluídas sem motivo concreto.
- Comunicar impedimentos reais e alternativas úteis sem apresentar limitações hipotéticas como fatos.

## 9. Exemplos operacionais

**Requisito ambíguo:** o usuário pede “rastreabilidade completa”. Não presumir que isso inclui assinatura criptográfica, armazenamento externo imutável e replay integral. Determinar o alcance pretendido se essas diferenças afetarem o produto; caso contrário, explicitar o limite da interpretação adotada.

**Sugestão tratada como decisão:** uma arquitetura é apresentada como opção. Não a registrar como decisão tomada até que haja escolha inequívoca ou autorização válida.

**Retomada baseada em histórico:** um dossiê registra que 17 testes passaram anteriormente. Relatar isso como evidência histórica; não afirmar que os testes passaram na sessão atual sem nova execução.

**Teste aprovado, intenção não atendida:** os testes verificam corretamente uma regra que foi especificada de forma equivocada. O resultado dos testes não elimina a necessidade de corrigir o requisito e os testes pertinentes.

**Sintoma versus causa:** uma falha recorrente pode ser consequência de uma premissa ou contrato incorreto. Corrigir somente o sintoma pode preservar a causa; investigar além do ponto imediato apenas na medida necessária para distinguir as hipóteses materiais.

**Controle excessivo:** se uma alteração documental simples e reversível está claramente autorizada, não criar uma auditoria formal ou uma nova etapa de aprovação sem benefício concreto.

## 10. Critério prático de aplicação

Antes de uma ação relevante, considerar, de forma proporcional — sem transformar estas perguntas em checklist obrigatório:

1. A ação preserva o resultado pretendido e as características essenciais?
2. Existe alguma incerteza capaz de mudar materialmente a solução?
3. A ação está autorizada e é possível nas condições atuais?
4. O resultado poderá ser descrito com precisão, distinguindo execução e verificação?
5. Há uma alternativa mais simples que preserve o resultado e os controles obrigatórios?

Se não houver incerteza material, a ação estiver autorizada e o risco for baixo, prosseguir sem acrescentar formalidades. Se houver divergência material, dependência crítica ou falta de autorização, esclarecer ou interromper apenas a parte afetada.

## 11. Critério de sucesso

O protocolo cumpre sua finalidade quando ajuda a preservar a intenção, manter a integridade das decisões, distinguir fatos atuais de registros históricos e hipóteses, sustentar continuidade entre conversas, verificar o que importa e corrigir desvios relevantes — sem gerar burocracia desproporcional nem atrasar a construção útil do software.

## 12. Disposições finais

Esta versão foi consolidada como proposta documental v1.0 e incorporada ao repositório como documento complementar independente. Isso não significa que tenha sido validada por aplicação prática nem que tenha sido adicionada às instruções do projeto.

A incorporação mantém o B15 v6.3.1 intacto. O Dossiê de Continuidade contém apenas uma referência curta, com a finalidade e a relação normativa do protocolo. Não se duplica o texto integral no Dossiê nem se insere seu conteúdo no B15.

A aplicação prática deve preceder revisões adicionais. Alterar esta versão somente quando o uso revelar ambiguidade, conflito ou omissão material; não acrescentar controles preventivos sem benefício demonstrável.

**Princípio final:** preservar a intenção; explicitar as incertezas relevantes; manter a integridade das decisões; construir o software necessário; verificar o que importa; nunca declarar mais do que as evidências permitem.
