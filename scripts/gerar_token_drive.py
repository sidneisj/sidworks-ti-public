"""Cria um token OAuth JSON local (Gmail leitura e Drive arquivos do app)."""
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow

BASE = Path(__file__).resolve().parents[1]
OAUTH = BASE / "creds" / "credentials_gmail.json"
TOKEN = BASE / "creds" / "token_gmail.json"
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/drive.file",
]
if not OAUTH.is_file():
    raise SystemExit("Crie creds/credentials_gmail.json conforme creds/README.md")
creds = InstalledAppFlow.from_client_secrets_file(str(OAUTH), SCOPES).run_local_server(port=0)
TOKEN.parent.mkdir(parents=True, exist_ok=True)
TOKEN.write_text(creds.to_json(), encoding="utf-8")
print("Token OAuth criado em creds/token_gmail.json. NÃO publique esse arquivo.")
