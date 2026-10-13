"""Verificações estáticas e conservadoras antes de publicar uma cópia limpa."""
from pathlib import Path
import re

RAIZ = Path(__file__).resolve().parents[1]
IGNORAR = {'.git', '.venv', '__pycache__', 'exports', '.pytest_cache'}
ARQUIVOS_PROIBIDOS = {
    '.env', 'creds/credentials.json', 'creds/credentials_gmail.json',
    'creds/token_gmail.json', 'creds/token_gmail.pickle',
    'creds/token.json', 'token_gmail.pickle', 'token_gmail.json',
}
PADROES = {
    'chave privada': re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
    'token GitHub conhecido': re.compile(r'\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{30,}\b'),
    'chave API Google': re.compile(r'\bAIza[0-9A-Za-z_-]{30,}\b'),
    'OAuth client ID': re.compile(r'\b\d{10,}-[a-zA-Z0-9_-]{20,}\.apps\.googleusercontent\.com'),
    'caminho local Windows': re.compile(r'[A-Z]:\\Users\\', re.I),
    'OneDrive corporativo': re.compile(r'OneDrive\s*-\s*PRODESP', re.I),
    'Google Alerts feed específico': re.compile(r'google\.com/alerts/feeds/\d+/\d+'),
}
EXTENSOES_TEXTO = {'.py', '.md', '.txt', '.json', '.ipynb', '.csv', '.yml', '.yaml', '.example', '.toml', '.ini', '.sh'}
erros = []
for arquivo in RAIZ.rglob('*'):
    if any(p in IGNORAR for p in arquivo.relative_to(RAIZ).parts) or not arquivo.is_file():
        continue
    relativo = arquivo.relative_to(RAIZ).as_posix()
    if relativo in ARQUIVOS_PROIBIDOS:
        erros.append((relativo, 'arquivo privado encontrado'))
    if arquivo.suffix.lower() not in EXTENSOES_TEXTO and arquivo.name not in {'.gitignore', '.env.example', '.gitattributes'}:
        continue
    conteudo = arquivo.read_text(encoding='utf-8', errors='replace')
    for nome, padrao in PADROES.items():
        if padrao.search(conteudo):
            erros.append((relativo, nome))
if erros:
    print('REVISÃO NECESSÁRIA:')
    for nome, motivo in erros:
        print(f'  {nome}: {motivo}')
    raise SystemExit(1)
print('OK: nenhuma correspondência encontrada nas verificações locais.')
print('A verificação não substitui auditoria manual ou varredura do histórico Git.')
