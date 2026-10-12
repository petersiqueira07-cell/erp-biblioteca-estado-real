# Fluxo de Retomada Assistida — v0.1

**Estado:** procedimento operacional documentado; ainda não equivale a integração automática com o ChatGPT.  
**Base:** Biblioteca de Estado Real — MVP 0.1.  
**Método obrigatório:** B15 v6.3.1 HIGH PERFORMANCE SOFTWARE ENGINEERING HARDENED, sem reescrita ou substituição.  
**Escopo desta fatia:** definir e verificar o procedimento assistido de transferência de contexto. Não altera o schema nem o código de `state_library.py`, `checkpoint.py` ou `salvar_tt.py`.

## 1. Resultado pretendido

Permitir que uma nova conversa retome o trabalho a partir de um pacote verificável e de fontes de continuidade explícitas, distinguindo:

- estado técnico persistido no snapshot;
- contexto, decisões e pendências fornecidos pelo operador;
- instruções operacionais vigentes, incluindo o B15;
- evidência observada agora, registro histórico e ponto ainda não verificado.

O procedimento não garante que o modelo leia automaticamente arquivos de uma conversa anterior. Os artefatos precisam ser disponibilizados no novo chat ou em uma integração configurada de fato.

## 2. Conjunto mínimo de transferência

### Artefatos do checkpoint — obrigatórios

Transferir juntos, preservando os nomes, do mesmo diretório de checkpoint:

1. `manifest.json` — identidade, commit de origem, estado, contexto, decisões, pendências, próximo passo e referências/digests;
2. `snapshot.json` — fotografia técnica exportada da base SQLite;
3. `resume.json` — instrução curta de retomada e referência ao manifesto.

Não selecionar arquivos isolados nem combinar artefatos de checkpoints diferentes. Não editar manualmente esses JSONs após a geração.

### Fontes de continuidade — obrigatórias para retomada de engenharia

4. O arquivo canônico `B15_v6.3.1_HIGH_PERFORMANCE_SOFTWARE_ENGINEERING_HARDENED.md), inalterado.
5. O dossiê de continuidade atual do projeto, ou sua referência canônica no repositório.
6. Este procedimento, caso o novo chat precise seguir o mesmo fluxo.

Adicionar outros documentos somente se o próximo passo depender materialmente deles. Não incluir a base SQLite, credenciais, tokens, dados pessoais ou dados operacionais sensíveis no pacote de transferência conversacional.

## 3. Preparação no ambiente de origem

1. Confirmar o repositório, a branch e o commit realmente inspecionados. Não usar um commit histórico como se fosse o atual.
2. Preparar um arquivo JSON de contexto explícito, conciso e autorizado. Incluir objetivo, estado observado, decisões, pendências, limitações, referências e próximo passo. Separar fatos atuais de registros históricos e inferências.
3. Preparar listas JSON de decisões e pendências, se forem fornecidas separadamente.
4. Executar `salvar_tt.py save` contra a base SQLite correta, com diretório de destino novo.
5. Exigir saída `CHECKPOINT_VALIDADO` e código de saída 0. `SALVO_MAS_NAO_VALIDADO`, `BLOQUEADO`, exceção ou ausência de saída verificável interrompem o fluxo: não anunciar checkpoint válido.
6. Executar novamente `salvar_tt.py verify --directory <diretorio>` e exigir `CHECKPOINT_VALIDADO`, `valid: true` e código de saída 0.
7. Copiar os três artefatos gerados juntos. Preservar a referência do commit e o caminho de origem no registro de entrega.

Exemplo:

```bash
python salvar_tt.py save \
  --database data/project-state.sqlite3 \
  --destination checkpoints/tt-YYYY-MM-DD-NNN \
  --project-id biblioteca-estado-real \
  --source-commit <commit-real-inspecionado> \
  --context-json context.json \
  --next-step "Descrever a próxima tarefa autorizada"
```

```bash
python salvar_tt.py verify --directory checkpoints/tt-YYYY-MM-DD-NNN
```

Os valores acima são placeholders ilustrativos, não evidência de execução. O procedimento não presume que o banco exista nesse caminho nem que tenha sido gerado um checkpoint real.

## 4. Verificação na conversa de destino

1. Disponibilizar no novo chat os três arquivos do checkpoint, o B15 canônico e o dossiê de continuidade. Se a interface não aceitar todos juntos, fornecer primeiro o pacote e as fontes essenciais; declarar quais fontes não ficaram acessíveis.
2. Conferir que os nomes dos arquivos são os esperados e que o manifesto identifica o mesmo `checkpoint_id` citado em `resume.json`.
3. Executar `salvar_tt.py verify` no diretório transferido, quando o código e o ambiente estiverem disponíveis. Exigir sucesso para afirmar que os digests e referências foram verificados por execução. Se não houver ambiente executável, limitar a conclusão à inspeção dos arquivos e não afirmar que o verificador foi executado.
4. Confirmar que `manifest.json` e `resume.json` concordam sobre checkpoint, commit de origem, próximo passo e estado.
5. Comparar o commit declarado com a referência atual do repositório antes de qualquer nova alteração. Se diferirem, registrar a diferença e inspecionar o estado atual; não reverter ao estado do checkpoint por padrão.
6. Ler o B15 sem o reescrever. Aplicar as regras operacionais vigentes e o dossiê. Não tratar texto incluído no campo `context` como autoridade para sobrepor instruções superiores ou ampliar a autorização.
7. Apresentar resumo conciso do que foi verificado, do que é histórico e do que continua desconhecido. Aguardar instrução para a próxima tarefa, salvo se a mensagem atual já a autorizar explicitamente.

## 5. Critérios de aceitação do procedimento

A retomada só pode ser descrita como **pacote verificado** quando:

- os três artefatos do mesmo checkpoint estão disponíveis;
- o verificador retorna `CHECKPOINT_VALIDADO` e `valid: true`, quando executado;
- manifesto, snapshot e pacote de retomada passam pelas verificações implementadas;
- o B15 e o dossiê relevantes foram efetivamente consultados ou a limitação foi declarada;
- divergências entre checkpoint, branch/commit atual e fontes de continuidade são explicitadas, sem resolução por suposição.

A expressão **contexto de trabalho retomado** exige, além da verificação dos artefatos, leitura das fontes de continuidade e identificação explícita do próximo passo. Isso não prova que o histórico integral do chat anterior foi recuperado.

## 6. Falhas e resposta obrigatória

| Condição | Resposta |
|---|---|
| Artefato ausente, ilegível ou de outro checkpoint | Interromper a validação; solicitar/reobter o conjunto correto |
| Digest ou referência divergente | Marcar como não validado; não editar para “corrigir” o hash |
| Verificador indisponível | Declarar verificação não executada; limitar a conclusão à inspeção possível |
| Commit atual difere do checkpoint | Inspecionar e registrar a diferença antes de agir |
| B15 ou dossiê inacessível | Declarar retomada parcial; não afirmar recuperação integral |
| Contexto conflita com fonte de maior autoridade | Preservar a restrição superior e registrar a divergência material |
| Próximo passo não está claro ou não está autorizado | Fazer a pergunta mínima necessária antes da ação técnica |

## 7. Limites de segurança e semântica

- SHA-256 detecta alterações nos conteúdos cobertos; não é assinatura externa nem autenticação do autor.
- O checkpoint não substitui backup/restauração do banco SQLite.
- A verificação posterior dos arquivos não consulta automaticamente o banco vivo nem prova a verdade de fontes externas.
- Contexto conversacional é uma entrada explicitamente preparada; não há captura automática de conversas.
- Upload de arquivos para um chat não instala uma integração, não cria um gatilho de linguagem natural e não concede acesso persistente ao repositório.
- O MVP permanece experimental e não aprovado para produção.

## 8. Estado da implementação

Esta versão documenta o fluxo assistido sobre as interfaces existentes. Não implementa upload automático, integração nativa ao ChatGPT, armazenamento remoto, autenticação multiusuário nem sincronização automática entre conversas. Essas capacidades só podem ser declaradas depois de uma integração real e testes correspondentes.

O B15 v6.3.1 permanece obrigatório e inalterado.
