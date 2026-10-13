# SidWorks TI — v1.0.0

**Autor:** Sidnei de Souza Júnior  
**Licença do código:** MIT

## Funcionalidades

- Demonstração offline com vagas fictícias e geração de PDF/DOCX.
- Coleta e preparação de oportunidades via RSS e Gmail (configuração própria necessária).
- Classificação, normalização e deduplicação de vagas.
- Integração configurável com Google Sheets e Google Drive.
- PDFs e documentos Word da execução real nomeados com timestamp; demonstração com nomes fixos.
- Testes automatizados de processamento, demonstração e segurança estática.

## Segurança e configuração

- Credenciais e tokens não estão incluídos; utilize `.env.example` e os modelos em `creds/`.
- Workflow automático do GitHub Actions desativado por padrão.
- Fontes DejaVu distribuídas com licença própria em `fonts/LICENSE-DejaVu.txt`.

## Limitações conhecidas

A demonstração offline e os testes locais foram executados com sucesso. As integrações Google do fluxo real exigem credenciais próprias e ainda não foram validadas de ponta a ponta com uma configuração externa nova.
