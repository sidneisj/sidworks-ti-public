"""Confere os escopos de um token OAuth JSON gerado localmente."""
from pathlib import Path
from google.oauth2.credentials import Credentials

TOKEN = Path(__file__).resolve().parents[1] / "creds" / "token_gmail.json"
if not TOKEN.exists():
    raise SystemExit("Token não encontrado. Execute python scripts/gerar_token_drive.py")
creds = Credentials.from_authorized_user_file(str(TOKEN))
print("Token válido:", creds.valid)
print("Escopos:")
for scope in (creds.scopes or []):
    print("-", scope)
