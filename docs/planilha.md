# Estrutura mínima da planilha Google

Crie uma planilha Google e compartilhe acesso de edição com a conta de serviço. No `.env`, configure `GOOGLE_SHEET_ID` com o ID extraído da URL da planilha.

- **Primeira aba (saída principal)**: `Vaga | Link | Short Link | Categoria`. O sistema limpa e atualiza essa aba.
- **Keywords**: cabeçalhos exatos `Keyword | Categoria`. Exemplo: `Python | Desenvolvimento/Sistemas`.
- **Links Sugeridos**: cabeçalhos exatos `Vaga | Link | Short Link`. Pode permanecer sem linhas de dados.
- **Blacklist** (opcional): pelo menos três colunas, com a terceira contendo links curtos que devem ser excluídos.
- Abas por categoria: são criadas pelo script conforme necessário.

**Importante:** use uma planilha de testes, pois o script **limpa e sobrescreve** a primeira aba e as abas de categoria.
