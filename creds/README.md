# Configuração de credenciais

Nunca publique chaves privadas, `.env` ou tokens. Os JSON `.example.json` são **esquemas fictícios**, não credenciais executáveis.

1. Crie um projeto no Google Cloud e ative as APIs **Google Sheets**, **Google Drive** e, se utilizar alertas do LinkedIn por e-mail, **Gmail**.
2. Crie uma conta de serviço, gere uma chave JSON e salve-a em `creds/credentials.json`. Compartilhe a planilha com o e-mail dessa conta.
3. Para habilitar Gmail, configure a tela de consentimento e crie um cliente OAuth do tipo **Aplicativo para computador**. Salve o download como `creds/credentials_gmail.json`.
4. Execute localmente `python scripts/gerar_token_drive.py` para conceder as permissões Gmail (leitura) e Drive (arquivos criados/abertos pelo app). O token ficará em `creds/token_gmail.json` e será ignorado pelo Git.
5. Para verificar o token: `python scripts/verificar_token.py`.
6. Configure `.env`, seguindo `.env.example`. O script usa `python-dotenv` para carregá-lo.

**Observação de segurança:** o projeto original usava `pickle`, mas a versão pública utiliza JSON para tokens OAuth. Não copie tokens antigos para este repositório. A permissão `drive.file` pode não ser suficiente para todas as operações em pastas/arquivos preexistentes, dependendo da autorização e do ambiente Google.
