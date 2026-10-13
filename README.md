# SidWorks TI — Automação de divulgação de vagas de TI

Projeto desenvolvido por **Sidnei de Souza Júnior** e utilizado para organizar e compartilhar oportunidades de tecnologia em um canal do WhatsApp. Durante a operação, o código-fonte permaneceu privado; esta versão pública apresenta a solução e permite sua adaptação.

**Status:** operação original encerrada; código legado aberto para estudos, portfólio e experimentação.

## Experimentar sem instalar nada (Google Colab)

[![Abrir no Google Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/sidneisj/sidworks-ti-public/blob/main/colab/SidWorksTI.ipynb)

O notebook público clona este repositório em um ambiente temporário do Colab, instala as dependências e executa `python main.py --demo` com **vagas fictícias**, sem solicitar credenciais Google, montar seu Drive ou alterar suas planilhas. Os relatórios PDF e DOCX gerados podem ser baixados ao final. **A execução do notebook no serviço Colab ainda precisa ser confirmada por um usuário.**

## Início rápido (demonstração sem contas Google)

**Windows (Git Bash):**

```bash
py -3 -m venv .venv
source .venv/Scripts/activate
python -m pip install -r requirements.txt
python main.py --demo
```

**Linux/macOS:**

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python main.py --demo
```

Os exemplos fictícios estão em `examples/`. Os relatórios são gerados em `exports/`, pasta ignorada pelo Git. Para executar os testes:

```bash
python -m unittest discover -s tests -v
python scripts/verificar_publicacao.py
```

Os testes de demonstração usam pastas temporárias próprias para evitar sobrescrever um PDF aberto.

## Demonstração offline — execute primeiro

Após criar e ativar o ambiente e instalar `requirements.txt`, execute:

```bash
python main.py --demo
```

O comando lê os arquivos fictícios em `examples/`, usa as funções de classificação,
normalização e deduplicação do código original e produz um **PDF por categoria** e um
**DOCX de mensagens para WhatsApp** na pasta `exports/`. Ele não utiliza Gmail,
Sheets, Drive, TinyURL nem credenciais Google. As vagas e URLs de `example.org` **não são reais**.

> O comando `python main.py` (sem `--demo`) executa o fluxo legado real,
> requer sua configuração Google e pode sobrescrever abas da planilha indicada.
> Não o utilize com uma planilha de produção antes de revisar a configuração.

## Tecnologias e arquitetura

**Python**, Google Alerts/RSS, Gmail API, Google Sheets API, Google Drive API, GitHub Actions (utilizado na automação original), FPDF2 e python-docx.

Consulte a [arquitetura do projeto](docs/arquitetura.md) e as [instruções da planilha](docs/planilha.md).

## Visão geral

Google Alerts (RSS) + alertas do LinkedIn recebidos no Gmail (opcionais) + links sugeridos → processamento Python → classificação por palavras-chave, normalização e deduplicação → Google Sheets → PDFs/DOCX → Google Drive (opcional) → publicação manual no WhatsApp.

A publicação em WhatsApp era manual; o sistema gerava o material a ser compartilhado. O fluxo real mantém nomes de PDF e DOCX com timestamp; a demonstração usa nomes fixos.

## Como executar (Python 3.11+ recomendado)

1. Clone **o novo repositório público** e abra um terminal na raiz do projeto.
2. Crie um ambiente virtual e instale `pip install -r requirements.txt`.
3. Copie `.env.example` para `.env` e configure `GOOGLE_SHEET_ID`, `RSS_FEEDS` e outros parâmetros. `WHATSAPP_CHANNEL_URL` é opcional: em branco, não é exibido no PDF.
4. Veja `docs/planilha.md` para criar uma planilha vazia exclusiva para testes. **A primeira aba e as abas de categorias serão sobrescritas.**
5. Veja `creds/README.md`: crie suas próprias credenciais Google e coloque `credentials.json` dentro de `creds/`. A autenticação Gmail é opcional quando se deseja trabalhar apenas com RSS.
6. Execute `python main.py`. As saídas serão salvas em `exports/`, a menos que `SIDWORKS_REPORTS_PATH` seja alterado.

Para autorizar o Gmail localmente, siga `creds/README.md` e execute `python scripts/gerar_token_drive.py`. Para experimentar no Colab sem contas Google, abra o [notebook de demonstração](colab/SidWorksTI.ipynb). O fluxo real com APIs Google exige credenciais próprias e **não é executado automaticamente** no notebook.

## Testes locais (sem autenticação Google)

Após instalar as dependências, execute:

```bash
python -m unittest discover -s tests -v
```

Estes testes verificam normalização, categorização, deduplicação e a geração offline de PDF/DOCX. **Não** validam as integrações Google.

## Segurança

- Nunca adicione `.env`, `creds/credentials.json`, `creds/credentials_gmail.json` nem tokens ao Git. Os arquivos `.example.json` são fictícios.
- Tokens OAuth são armazenados como JSON na versão pública (`creds/token_gmail.json`); tokens antigos `.pickle` não são necessários.
- O histórico do repositório privado **não deve ser copiado** para o público: continha arquivos sensíveis agora revogados.
- A versão pública não carrega arquivos de token `.pickle`; nunca publique tokens antigos.
- O workflow GitHub Actions incluído não agenda nem executa o pipeline automaticamente.
- A autorização do Google requer credenciais e permissões próprias.

## Projeto original e portfólio

**Autoria:** Sidnei de Souza Júnior. O projeto foi desenvolvido e operado antes da abertura do código, com divulgação de oportunidades de TI por meio de mensagens preparadas para WhatsApp. O código-fonte original permaneceu em repositório privado; este repositório público apresenta uma versão revisada, documentada e com dados de exemplo.


Este repositório documenta seu funcionamento e o desenvolvimento técnico: integrações Google, coleta RSS/Gmail, tratamento e classificação de registros, deduplicação, geração de relatórios e automação. A publicação do código ocorreu após o encerramento da operação.

## Limitações e transparência

Este projeto foi originalmente desenvolvido para um ambiente particular (Google Cloud/Drive e planilha configurada). A versão pública recebeu ajustes de portabilidade, mas ainda **não passou por teste de ponta a ponta com contas Google de terceiros**. Algumas operações da API podem exigir adaptação à política de permissões vigente. Use inicialmente uma planilha separada para evitar perda de dados.

## Licença

O código-fonte do SidWorks TI é distribuído sob a **Licença MIT**. Consulte [`LICENSE`](LICENSE).

Copyright (c) 2026 **Sidnei de Souza Júnior**. A licença permite utilização, modificação e redistribuição do código, inclusive comercial, desde que o aviso de copyright e os termos sejam preservados. As fontes DejaVu são componentes de terceiros e mantêm seus próprios termos em [`fonts/LICENSE-DejaVu.txt`](fonts/LICENSE-DejaVu.txt).
