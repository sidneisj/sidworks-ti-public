# SidWorks TI — desenvolvido por Sidnei de Souza Júnior
# Licença MIT: consulte LICENSE.

# ===============================
# 📌 Instalação das bibliotecas
# ===============================

# ===============================
# 📌 Imports
# ===============================
import os, base64, re, requests
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent / ".env")
import feedparser
from urllib.parse import urlparse, parse_qs, unquote
from bs4 import BeautifulSoup

import pyshorteners  # ✅ para encurtar os links

import gspread
from oauth2client.service_account import ServiceAccountCredentials

from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

import requests

# from google.colab import drive
# drive.mount('/content/drive')

import os, sys

# O bloqueio de execução fica na entrada CLI, não na importação do módulo.
# Assim funções de processamento podem ser testadas sem efeitos colaterais.
LOCK_FILE = str(Path(__file__).resolve().parent / ".sidworks_execucao")


def chave_ordenacao(vaga):
    if isinstance(vaga, dict):
        titulo = vaga.get("vaga") or vaga.get("Vaga", "")
    else:
        titulo = vaga[0] if vaga else ""

    # Detecta se contém a tag [SUGERIDO]
    sugerido = "[SUGERIDO]" in titulo.upper()

    # Limpa para ordenação alfabética sem interferência da tag
    titulo_limpo = re.sub(r'\[SUGERIDO\]', '', titulo, flags=re.IGNORECASE).strip().lower()

    # Retorna tupla: primeiro os sugeridos (False vem antes de True)
    return (not sugerido, titulo_limpo)

def remover_emojis(texto):
    # Remove qualquer emoji ou caractere fora do BMP (Basic Multilingual Plane)
    return re.sub(r'[\U00010000-\U0010ffff]', '', texto)

def encurtar_tinyurl(url, timeout=10):
    """
    Encurta o link usando TinyURL.
    timeout = 10 segundos por padrão (ajustável)
    """
    try:
        # 1ª tentativa: TinyURL
        resp = requests.get("https://tinyurl.com/api-create.php" + "?" + __import__("urllib.parse", fromlist=["urlencode"]).urlencode({"url": url}), timeout=timeout)
        if resp.status_code == 200 and resp.text.strip().startswith("http"):
            return resp.text.strip()
        else:
            print(f"⚠️ TinyURL falhou para {url} (status {resp.status_code}) → retornando original")

        # 2ª tentativa: is.gd
        resp2 = requests.get(f"https://is.gd/create.php?format=simple&url={url}", timeout=timeout)
        if resp2.status_code == 200 and resp2.text.strip().startswith("http"):
            return resp2.text.strip()
        else:
            print(f"⚠️ is.gd falhou para {url} (status {resp2.status_code})")

    except Exception as e:
        print(f"⚠️ Erro ao encurtar {url}: {e}")

    # fallback final: retorna o link original
    return url

import os
import time
import platform

# ======================
# 🔍 Detectar Ambiente
# ======================
def is_colab():
    try:
        import google.colab
        return True
    except ImportError:
        return False

def is_github_actions():
    return os.environ.get("GITHUB_ACTIONS") == "true"

def ambiente():
    if is_github_actions():
        return "actions"
    elif is_colab():
        return "colab"
    else:
        return "local"


# ===============================
# ⚙️ Configurações e listas de controle
# ===============================

# Domínios que devem ser ignorados
DOMAIN_BLACKLIST = {
    "glassdoor.com",
    "reddit.com",
    "mygwork.com"
    # "vagas.com",       # exemplo adicional
    # "infojobs.com.br", # exemplo adicional
}

# LinkedIn Senders
LINKEDIN_SENDERS = [
    'jobalerts-noreply@linkedin.com',
    'jobs-listings@linkedin.com'
]

# Feeds do Google Alerts
RSS_FEEDS = [
    line.strip() for line in os.getenv("RSS_FEEDS", "").split(",") if line.strip()
]

# ===============================
# 📌 Funções auxiliares (Google Alerts)
# ===============================
def try_unquote(s, max_rounds=3):
    if not isinstance(s, str):
        return s
    last = s
    for _ in range(max_rounds):
        new = unquote(last)
        if new == last:
            break
        last = new
    return last

def extract_first_url(text):
    if not text:
        return None
    m = re.search(r"https?://[^\s'\"<>]+", text)
    return m.group(0) if m else None

from urllib.parse import urlparse

# Checa se a URL é de um dominio que está na Blacklist de dominios
def dominio_esta_blacklistado(url, domain_blacklist=DOMAIN_BLACKLIST):
    """
    Retorna True se o hostname do URL contiver qualquer domínio da domain_blacklist.
    Trata exceções e URLs vazias de forma segura.
    """
    try:
        if not url:
            return False
        parsed = urlparse(url)
        hostname = (parsed.netloc or "").lower().split(":")[0]  # remove porta
        for bad in domain_blacklist:
            if bad.lower() in hostname:
                return True
        return False
    except Exception:
        return False


import re
from urllib.parse import urlparse, parse_qs

def limpar_link(raw_url, entry=None):
    """
    Limpa/normaliza URLs:
    - Decodifica percent-encoding repetidamente
    - Extrai real URL de redirects do Google (q, url, u)
    - Se for LinkedIn jobs (com /comm/ ou sem), retorna canonical: https://www.linkedin.com/jobs/view/<ID>/
    - Caso contrário remove query/fragment e retorna URL decodificada
    """
    try:
        # fallback: tenta extrair do summary se raw_url vazio
        if not raw_url and entry is not None:
            cand = extract_first_url(getattr(entry, "summary", "") or "")
            return try_unquote(cand) if cand else raw_url

        if not raw_url:
            return raw_url

        # decodifica %25 -> % etc
        url = try_unquote(raw_url)

        # se for um google redirect (ex: https://www.google.com/url?...&url=REALURL)
        parsed = urlparse(url)
        if "google.com" in parsed.netloc and parsed.query:
            qs = parse_qs(parsed.query)
            for key in ("q", "url", "u"):
                if key in qs and qs.get(key):
                    candidate = try_unquote(qs[key][0])
                    # atualiza url/parsed para o valor real e segue
                    url = candidate
                    parsed = urlparse(url)
                    break

        # tenta extrair a primeira http(s) se ainda houver algo estranho
        if "url=" in url and url.count("http") > 0:
            m_ex = extract_first_url(url)
            if m_ex:
                url = try_unquote(m_ex)
                parsed = urlparse(url)

        # —— Normalização específica do LinkedIn —— #
        # Captura tanto /jobs/view/<id> quanto /comm/jobs/view/<id> e variações com query
        m = re.search(r'linkedin\.com(?:/comm)?/jobs/(?:view/)?(\d+)', url)
        if m:
            job_id = m.group(1)
            # canonical link (sempre com /jobs/view/<id>/)
            return f"https://www.linkedin.com/jobs/view/{job_id}/"

        # Fallback genérico: remove query e fragment e retorna decoded
        cleaned = parsed._replace(query="", fragment="").geturl()
        return try_unquote(cleaned)

    except Exception:
        return raw_url



def limpar_html(texto):
    if not texto:
        return ""
    return BeautifulSoup(texto, "html.parser").get_text().strip()

import unicodedata

def normalize_text(text):
    """
    Remove acentos e deixa tudo em minúsculas para comparação.
    """
    text = unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode('ASCII')
    return text.lower()

# ===============================
# 🔁 Função de Deduplicação Global
# ===============================
def deduplicar_vagas(dados):
    """
    Remove duplicatas considerando o ID da vaga (LinkedIn) ou URL normalizada.
    Retorna uma lista limpa e sem duplicados.
    """
    links_vistos = set()
    resultado = []
    for titulo, link, short_link, categoria in dados:
        chave = obter_chave_deduplicacao(link)
        if chave not in links_vistos:
            resultado.append([titulo, link, short_link, categoria])
            links_vistos.add(chave)
        else:
            print(f"⚠️ Duplicado removido (deduplicação global): {link}")
    return resultado

def carregar_keywords(spreadsheet):
    """
    Lê a aba 'Keywords' e retorna uma lista de tuplas (keyword, categoria)
    """
    try:
        aba = spreadsheet.worksheet("Keywords")
        registros = aba.get_all_records()  # cada registro = {"Keyword": ..., "Categoria": ...}
        keywords = [(normalize_text(r["Keyword"]), r["Categoria"]) for r in registros if r["Keyword"]]
        print(f"✅ {len(keywords)} keywords carregadas.")
        return keywords
    except Exception as e:
        print(f"⚠️ Erro ao ler aba 'Keywords': {e}")
        return []

def categorizar_titulo(titulo, keywords_lookup):
    """
    Categoriza o título com base nas keywords carregadas do Excel.
    """
    t = normalize_text(titulo)
    categorias_encontradas = []

    for kw, cat in keywords_lookup:
        if kw in t:
            categorias_encontradas.append(cat)

    if not categorias_encontradas:
        categorias_encontradas.append("Outros")  # fallback

    # Remove duplicatas e mantém a ordem
    return ", ".join(list(dict.fromkeys(categorias_encontradas)))


#Carregar Links Sugeridos
def carregar_links_sugeridos(spreadsheet, keywords_lookup):
    """
    Lê a aba 'Links Sugeridos' da planilha e retorna uma lista de dicionários no mesmo formato das demais vagas.
    """
    try:
        aba = spreadsheet.worksheet("Links Sugeridos")
        registros = aba.get_all_records()

        links_sugeridos = []
        for r in registros:
            titulo = r.get("Vaga", "").strip()
            link = r.get("Link", "").strip()
            short_link = r.get("Short Link", "").strip()
            categoria = categorizar_titulo(titulo, keywords_lookup)

            # O prefixo será adicionado depois (para evitar duplicação)

            links_sugeridos.append({
                "Vaga": titulo,
                "Link": link,
                "Short Link": short_link,
                "Categoria": categoria,
                "sugerido": True
            })

        print(f"\n✅ {len(links_sugeridos)} links sugeridos carregados.")

        return links_sugeridos

    except Exception as e:
        print(f"⚠️ Erro ao ler aba 'Links Sugeridos': {e}")
        return []


# ===============================
# 📌 Gmail Auth
# ===============================
def gmail_authenticate():
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow
    SCOPES = ["https://www.googleapis.com/auth/gmail.readonly", "https://www.googleapis.com/auth/drive.file"]

    amb = ambiente()

    if amb == "colab":
        TOKEN_PATH = os.path.join(os.getenv("SIDWORKS_BASE_PATH", str(Path(__file__).resolve().parent)), "creds/token_gmail.json")

    elif amb == "actions":
        TOKEN_PATH = "./creds/token_gmail.json"  # ← EXACTAMENTE ONDE O ACTIONS CRIA

    else:
        TOKEN_PATH = os.path.join(os.getenv("SIDWORKS_BASE_PATH", str(Path(__file__).resolve().parent)), "creds/token_gmail.json")

    creds = None

    # 🔍 Tenta carregar token existente
    if os.path.exists(TOKEN_PATH):
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
        except:
            creds = None

    # 🔁 Se token inválido, não tenta abrir navegador no Actions/Colab
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if amb in ["colab", "actions"]:
                print("⚠️ Gmail desativado: não é permitido abrir navegador no ambiente atual.")
                return None

            # Ambiente LOCAL → pode abrir navegador normalmente
            flow = InstalledAppFlow.from_client_secrets_file(
                os.path.join(os.getenv("SIDWORKS_BASE_PATH", str(Path(__file__).resolve().parent)), "creds", "credentials_gmail.json"), SCOPES
            )
            creds = flow.run_local_server(port=0)

        # Salva token atualizado
        Path(TOKEN_PATH).parent.mkdir(parents=True, exist_ok=True)
        Path(TOKEN_PATH).write_text(creds.to_json(), encoding="utf-8")

    return build("gmail", "v1", credentials=creds)


def get_linkedin_jobs(service, keywords_lookup, max_results=5):
    jobs = []
    for sender in LINKEDIN_SENDERS:
        results = service.users().messages().list(
            userId='me', q=f'from:{sender}', maxResults=max_results
        ).execute()
        messages = results.get('messages', [])
        for msg in messages:
            txt = service.users().messages().get(userId='me', id=msg['id']).execute()
            payload = txt['payload']
            headers = payload.get('headers', [])
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '(sem assunto)')

            body = ""
            if 'parts' in payload:
                for part in payload['parts']:
                    if part['mimeType'] == 'text/html':
                        data = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8-sig')
                        body = data
                        break
            else:
                data = payload['body'].get('data')
                if data:
                    body = base64.urlsafe_b64decode(data).decode('utf-8-sig')

            soup = BeautifulSoup(body, 'html.parser')
            for a in soup.find_all('a', href=True):
                title = a.get_text(strip=True)

                # Se não houver título útil, marca como "Sem título"
                if not title or len(title) < 3:
                    title = "Sem título"

                href_raw = a['href'].strip()
                href = limpar_link(href_raw)

                # Ignora se o link for de domínio bloqueado
                if dominio_esta_blacklistado(href):
                    print(f"🔕 Ignorado (domínio bloqueado): {href}")
                    continue

                if not href or not href.startswith("http"):
                    continue

                if ('/jobs/view/' in href) or ('/jobs-' in href):
                    categoria = categorizar_titulo(title, keywords_lookup)
                    jobs.append([title, href, categoria])

    return jobs



# Remover duplicatas (deduplicação LinkedIn baseada apenas no ID da vaga)
def obter_chave_deduplicacao(link):
    if not link:
        return ""
    link_limpo = limpar_link(link)
    # remove trailing slash e query params irrelevantes
    parsed = urlparse(link_limpo)
    normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip('/')
    m = re.search(r'/jobs/view/(\d+)', normalized)
    if m:
        return f"linkedin:{m.group(1)}"
    return normalized


# =====================================================
# 🔁 UNIFICAÇÃO, NORMALIZAÇÃO E DEDUPLICAÇÃO CORRETAS
# =====================================================

# Função auxiliar para formato padronizado
def make_record(titulo, link, short_link="", categoria="Outros", sugerido=False):
    titulo = (titulo or "").strip()
    link = (link or "").strip()
    short_link = (short_link or link or "").strip()
    return [titulo, link, short_link, categoria, bool(sugerido)]

# ===============================
# 📌 Criação do arquivo em PDF com todas as vagas
# ===============================

import pandas as pd
from fpdf import FPDF, XPos, YPos

# -------------------------------
# Função para limpar caracteres problemáticos
# -------------------------------
def limpar_texto(texto):
    if pd.isna(texto):
        return ""
    return str(texto)\
        .replace("—", "-")\
        .replace("–", "-")\
        .replace("“", '"')\
        .replace("”", '"')\
        .replace("…", "...")


# -------------------------------
# Classe PDF com cabeçalho e rodapé
# -------------------------------
class PDFComCabecalhoRodape(FPDF):
    def header(self):
        self.set_text_color(0, 0, 0)
        texto2 = os.getenv("WHATSAPP_CHANNEL_URL", "").strip()
        texto1 = "SidWorks TI - " if texto2 else "SidWorks TI"

        self.set_font("DejaVu", "B", 9)
        largura1 = self.get_string_width(texto1)
        self.set_font("DejaVu", "I", 9)
        largura2 = self.get_string_width(texto2)

        largura_total = largura1 + largura2
        self.set_x((self.w - largura_total) / 2)

        self.set_font("DejaVu", "B", 9)
        self.write(10, texto1)
        self.set_font("DejaVu", "I", 9)
        self.write(10, texto2)
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font("DejaVu", "I", 9)
        self.set_text_color(100, 100, 100)
        data_hora = datetime.now().strftime("%d/%m/%Y %H:%M")
        self.cell(0, 10, f"Atualizado em: {data_hora} | Página {self.page_no()}", align="C")

# -------------------------------
# Função principal para gerar PDF
# -------------------------------
def gerar_pdf_vagas_por_aba(
    spreadsheet,
    categorias,
    urls_blacklist=set(),
    dados_sem_dup=None,
    base_path=".",
    arquivo_pdf="vagas.pdf",
    modo_demo=False,
):
    """
    Gera PDF de vagas por categoria usando diretamente a lista deduplicada 'dados_sem_dup',
    sem depender da aba 'Todas as Vagas'. Agora ignora a categoria 'Outros'.
    """

    categorias = [c for c in categorias if c.upper() != "OUTROS"]

    if dados_sem_dup is None:
        raise ValueError("❌ ERRO: 'dados_sem_dup' não foi passado para gerar_pdf_vagas_por_aba()")

    dados_base = dados_sem_dup

    pdf = PDFComCabecalhoRodape()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Adiciona fontes
    pdf.add_font('DejaVu', '', os.path.join(base_path, 'fonts/DejaVuSans.ttf'))
    pdf.add_font('DejaVu', 'B', os.path.join(base_path, 'fonts/DejaVuSans-Bold.ttf'))
    pdf.add_font('DejaVu', 'I', os.path.join(base_path, 'fonts/DejaVuSans-Oblique.ttf'))

    recuo = 5
    cor_linha = (200, 200, 200)
    cor_titulo = (230, 240, 255)

    # ✅ Agrupa dados por categoria, ignorando 'Outros'
    categorias_filtradas = {}
    for cat in categorias:
        if cat.upper() == "OUTROS":
            print(f"⚠️ Categoria '{cat}' ignorada no PDF.")
            continue

        grupo = []
        for row in dados_base:
            titulo, link, short, categoria, sugerido = row

            if sugerido and "[SUGERIDO]" not in titulo.upper():
                titulo = f"[SUGERIDO] {titulo}"

            tipos = [t.strip() for t in categoria.split(",")]
            link_limpo = limpar_link(short)

            if cat in tipos and link_limpo not in urls_blacklist:
                grupo.append([titulo, link, short, cat])

        categorias_filtradas[cat] = grupo

    # ===========================
    # Cabeçalho inicial do PDF
    # ===========================
    pdf.add_page()
    pdf.ln(8)
    pdf.set_font("DejaVu", 'B', 20)
    pdf.set_text_color(0, 50, 100)
    pdf.cell(0, 12, "SidWorks TI", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
    pdf.set_font("DejaVu", 'I', 12)
    pdf.set_text_color(50, 50, 50)
    pdf.cell(0, 10, "Por quem vive TI, para quem quer evoluir.", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
    pdf.ln(8)

    # Introdução
    introducao = (
        "Este relatório reúne oportunidades de TI selecionadas de fontes configuradas pelo operador, "
        "organizadas em categorias para facilitar a consulta. "
        "Confirme a data de publicação e a disponibilidade de cada vaga antes de se candidatar."
    )
    canal = os.getenv("WHATSAPP_CHANNEL_URL", "").strip()
    if canal:
        introducao += f"\n\nCanal de divulgação: {canal}"
    if modo_demo:
        introducao = (
            "DEMONSTRAÇÃO OFFLINE — TODAS AS VAGAS DESTE RELATÓRIO SÃO FICTÍCIAS. "
            "Este exemplo mostra classificação, deduplicação e exportação em PDF "
            "do projeto SidWorks TI. Não utilize os links como anúncios reais."
        )
    pdf.set_font("DejaVu", '', 12)
    pdf.set_text_color(0, 0, 0)
    pdf.multi_cell(pdf.w - pdf.l_margin - pdf.r_margin - 5, 7, introducao)
    pdf.ln(10)

    # Total de vagas
    total_vagas = sum(len(v) for v in categorias_filtradas.values() if v)
    pdf.set_font("DejaVu", 'B', 12)
    pdf.set_text_color(0, 50, 150)
    pdf.cell(0, 10, f"Total de vagas listadas: {total_vagas}", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(8)
    pdf.set_draw_color(180, 180, 180)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(6)

    # ===============================
    # SUMÁRIO (ÍNDICE CLICÁVEL)
    # ===============================
    pdf.set_font("DejaVu", 'B', 14)
    pdf.cell(0, 10, "Sumário de Categorias (selecione para navegar):", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(3)
    links_categorias = {}
    for cat, grupo in categorias_filtradas.items():
        if grupo:
            links_categorias[cat] = pdf.add_link()
    for i, (cat, link_id) in enumerate(links_categorias.items(), start=1):
        pdf.cell(0, 8, f"{i}. {cat} ({len(categorias_filtradas[cat])})",
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT, link=link_id)
    pdf.ln(8)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(6)

    # ===============================
    # LISTAGEM POR CATEGORIA
    # ===============================
    for cat, grupo in categorias_filtradas.items():
        if not grupo:
            continue
        pdf.add_page()
        pdf.set_link(links_categorias[cat])
        pdf.set_fill_color(*cor_titulo)
        pdf.set_font("DejaVu", 'B', 14)
        pdf.cell(0, 10, f"{cat} ({len(grupo)})", new_x=XPos.LMARGIN, new_y=YPos.NEXT, fill=True)
        pdf.ln(2)
        grupo = sorted(grupo, key=chave_ordenacao)
        for titulo, link, short, categoria in grupo:
            titulo = limpar_texto(titulo)
            short = limpar_texto(short)
            pdf.set_x(pdf.l_margin + recuo)
            pdf.set_font("DejaVu", '', 11)
            pdf.multi_cell(0, 8, f"• {titulo}")
            pdf.set_x(pdf.l_margin + recuo)
            pdf.set_text_color(0, 0, 255)
            pdf.set_font("DejaVu", 'I', 10)
            pdf.multi_cell(0, 8, short, link=short)
            pdf.set_text_color(0, 0, 0)
            pdf.ln(1)
            pdf.set_draw_color(*cor_linha)
            pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
            pdf.ln(1)

    # Final
    pdf.set_font("DejaVu", 'I', 11)
    pdf.multi_cell(0, 8,
        "Muito obrigado por acreditar neste projeto e por ajudar a espalhar oportunidades em TI! "
        "Compartilhe o PDF com colegas e amigos.")
    pdf.ln(5)
    pdf.output(arquivo_pdf)
    print(f"\n✅ PDF gerado com sucesso: {arquivo_pdf}")



# ===============================
# 📌 GERAÇÃO DO ARQUIVO EM WORD PARA COLAR NO WHASTAPP
# ===============================

# ===============================
# 📌 Dependências adicionais
# ===============================
# pip install python-docx

from docx import Document
from docx.shared import Pt
import random
from datetime import datetime
import os

# ===============================
# 📌 Lista de mensagens diárias
# ===============================
mensagens_diarias = [
    "🌞 Bom dia! Cada novo dia traz novas oportunidades. Descubra as vagas que podem transformar sua carreira!",
    "💼 Hoje é dia de avançar! Explore as oportunidades e dê um passo a frente rumo ao emprego dos seus sonhos.",
    "✨ Novo dia, novas chances! Acredite no seu potencial e encontre a oportunidade certa para você.",
    "🚀 Hora de se destacar! Veja as vagas que selecionamos e comece o dia inspirado a alcançar seus objetivos.",
    "💡 Comece o dia com energia! Novas vagas estão esperando por você. É hora de explorar e se candidatar.",
    "🌟 Oportunidades aparecem todos os dias! Não perca tempo e confira as vagas fresquinhas que preparamos.",
    "🔑 Cada candidatura é uma porta aberta. Hoje pode ser o dia de conquistar algo incrível!",
    "🎯 Foque no seu objetivo! Descubra vagas que combinam com seu talento e potencial.",
    "💪 Acredite em você! Novas oportunidades surgiram e você está mais próximo do seu próximo emprego.",
    "🌱 Hoje é um bom dia para crescer! Explore as vagas e dê passos firmes rumo ao seu futuro.",
    "📌 Não espere, faça acontecer! Veja as oportunidades que podem transformar sua rotina profissional.",
    "⚡ Mova-se com energia! Cada vaga é uma chance de chegar mais perto do trabalho que você merece.",
    "⚡ Novos desafios te esperam! Confira as oportunidades e escolha seu próximo caminho.",
    "✍️ Um novo dia, uma nova chance de escrever sua história profissional. Confira as vagas disponíveis!",
    "🎉 Hoje pode ser o início de algo grande! Explore as oportunidades que selecionamos para você.",
    "🏆 Oportunidades não esperam! Veja as vagas do dia e avance rumo à sua conquista profissional.",
    "🌻 Comece o dia inspirado! Descubra vagas que fazem sentido para seu talento e potencial.",
    "🔥 A energia do dia é sua aliada! Confira as oportunidades e dê o próximo passo na carreira.",
    "🌟 Pequenas ações levam a grandes resultados. Explore as vagas e transforme seu dia!",
    "💡 Novas portas estão se abrindo! Descubra as oportunidades e prepare-se para crescer.",
    "🚀 Hoje é dia de ir mais longe! Veja as vagas selecionadas e avance na sua jornada profissional.",
    "🌞 Comece o dia motivado! Cada oportunidade é um passo para o futuro que você deseja.",
    "✨ Inspire-se e atue! Explore as vagas do dia e aproxime-se da carreira dos seus sonhos.",
    "🎯 Objetivos claros, ações certas! Veja as vagas e encontre o próximo desafio para sua carreira.",
    "💼 Hoje pode ser decisivo! Descubra oportunidades fresquinhas e faça acontecer.",
    "🌱 Cada candidatura é uma semente. Confira as vagas e plante seu futuro profissional.",
    "🔑 Oportunidades estão ao alcance! Veja as vagas do dia e abra novas portas.",
    "⚡ Um dia cheio de possibilidades! Explore as oportunidades e avance em direção ao seu objetivo.",
    "⚡ O dia começou! Aproveite as vagas selecionadas e dê passos firmes rumo ao seu sucesso.",
    "💪 Acredite no seu potencial! Hoje pode ser o dia em que você encontra a oportunidade certa."
]

# ===============================
# 📌 Função para sortear a mensagem do dia
# ===============================
def sortear_mensagem_diaria(seed=None):
    if seed is not None:
        random.seed(seed)
    return random.choice(mensagens_diarias)

# ===============================
# 📌 Mensagens para compartilhar o PDF com todas as vagas
# ===============================
mensagens_pdf = [
    "📎 Aqui está o PDF completo com todas as vagas atualizadas do dia! Explore por categoria e encontre a ideal para você. 💼",
    "💡 Todas as oportunidades de hoje reunidas em um só lugar! Baixe o PDF e confira as vagas por área.",
    "🚀 Confira abaixo o PDF com todas as vagas organizadas por categoria. Uma delas pode ser sua próxima conquista!",
    "📘 PDF diário de vagas disponível! Veja as oportunidades e prepare-se para dar o próximo passo na sua carreira.",
    "🌟 Todas as vagas do dia em um só arquivo! Abra o PDF e descubra novas possibilidades profissionais.",
    "💼 Oportunidades reunidas por categoria! Baixe o PDF e encontre aquela que combina com o seu perfil.",
    "🎯 As vagas do dia estão aqui! No PDF abaixo, você encontra todas as oportunidades atualizadas.",
    "📊 Aqui está o relatório completo de vagas! Organizado por área para facilitar sua busca.",
    "✨ Quer ver todas as vagas do dia? O PDF abaixo traz a lista completa separada por categoria.",
    "🔍 Todas as oportunidades reunidas em um só clique! Baixe o PDF e veja o que preparamos hoje.",
    "☕ Comece o dia conferindo o PDF com todas as vagas disponíveis. Pode ter algo feito sob medida pra você!",
    "📄 O PDF completo com as vagas de hoje está aqui! Explore as categorias e encontre a sua oportunidade.",
    "💪 Todas as vagas reunidas num só lugar! Baixe o PDF e encontre o trabalho que te inspira.",
    "🎉 Confira o PDF do dia com todas as vagas encontradas! Novas oportunidades te esperam.",
    "📂 Todas as vagas organizadas em um só arquivo. Veja o PDF abaixo e boa sorte nas candidaturas!",
    "⚡ PDF atualizado! Todas as categorias com vagas fresquinhas para você explorar hoje mesmo.",
    "⚡  Aqui está o PDF com todas as vagas do dia. Navegue, explore e escolha o seu próximo desafio!",
    "🧭 Encontre seu caminho! O PDF abaixo traz todas as vagas organizadas para facilitar sua busca.",
    "📌 PDF completo do dia disponível! Veja todas as oportunidades em um só lugar.",
    "🌻 Reunimos todas as vagas pra você! Confira o PDF abaixo e encontre sua próxima conquista profissional."
]

# ===============================
# 📌 Função para sortear a mensagem do PDF
# ===============================
def sortear_mensagem_pdf(seed=None):
    if seed is not None:
        random.seed(seed)
    return random.choice(mensagens_pdf)


# ===============================
# 📌 Funções principais
# ===============================
def obter_vagas_por_aba(spreadsheet, categorias, urls_blacklist=set()):
    """
    Lê cada aba da planilha (uma por categoria) e retorna dict {categoria: [rows...]},
    onde row = dict{'vaga','link','short_link','categoria'}.
    Ignora a aba 'OUTROS'.
    """
    vagas_por_cat = {}
    for cat in categorias:
        if cat.upper() == "OUTROS":  # Ignora a aba OUTROS
            print(f"⚠️ Aba '{cat}' ignorada.")
            continue

        try:
            aba = spreadsheet.worksheet(cat)
            dados = aba.get_all_values()
        except Exception:
            print(f"⚠️ Aba '{cat}' não encontrada — ignorando.")
            continue

        if not dados or len(dados) < 2:
            print(f"⚠️ Aba '{cat}' vazia.")
            continue

        header = [h.strip().lower() for h in dados[0]]
        vagas = []
        for row in dados[1:]:
            if len(row) < 4:
                row = row + [""] * (4 - len(row))
            vaga = row[0].strip()
            link = row[1].strip()
            short_link = row[2].strip() or link
            categoria = cat
            link_limpo = limpar_link(short_link)
            if link_limpo in urls_blacklist:
                continue
            if dominio_esta_blacklistado(link_limpo):
                print(f"🔕 Ignorado na planilha (domínio bloqueado): {link_limpo}")
                continue
            vagas.append({
                "vaga": vaga,
                "link": link,
                "short_link": short_link,
                "categoria": categoria
            })
        vagas_por_cat[cat] = vagas
    return vagas_por_cat


def sortear_vagas_por_categoria(vagas_por_cat, min_vagas=5, max_vagas=5, seed=None):
    """Sorteia de 5 a 10 vagas (ajustável) por categoria."""
    if seed is not None:
        random.seed(seed)
    amostras = {}
    for cat, lista in vagas_por_cat.items():
        if not lista:
            amostras[cat] = []
            continue
        n_disp = len(lista)
        n_sorteio = min(n_disp, random.randint(min_vagas, max_vagas))
        amostras[cat] = random.sample(lista, n_sorteio)
    return amostras

def montar_texto_post_categoria(cat, vagas_selecionadas):
    """Formata o texto do post para WhatsApp."""
    if not vagas_selecionadas:
        return None  # Retorna None para ignorar categorias sem vagas
    linhas = []
    linhas.append(f"💼 *{cat}*\n")
    for i, v in enumerate(vagas_selecionadas, start=1):
        titulo = v.get("vaga") or "Vaga"
        short = v.get("short_link") or v.get("link") or ""
        if len(titulo) > 120:
            titulo = titulo[:117].rstrip() + "..."
        linhas.append(f"{i}) {titulo}\n{short}\n")
    linhas.append("📎 Veja mais abaixo o PDF com todas as vagas encontradas dessa categoria.\n")
    return "\n".join(linhas)


def gerar_word_com_posts(amostras, mensagem_dia, mensagem_pdf,
                         arquivo_docx="mensagens_whatsapp.docx",
                         titulo_documento="SidWorks TI - Mensagens para WhatsApp"):
    """Cria apenas o arquivo .docx com todas as mensagens formatadas."""
    doc = Document()
    doc.core_properties.title = titulo_documento
    doc.add_heading(titulo_documento, level=1)
    doc.add_paragraph(f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}").italic = True
    doc.add_paragraph("")

    # Mensagem do dia
    p_msg = doc.add_paragraph()
    run_msg = p_msg.add_run(mensagem_dia + "\n\n")
    run_msg.font.size = Pt(12)

    # Percorre categorias
    for cat, vagas in amostras.items():
        if not vagas:
            continue  # Ignora categorias sem vagas
        texto_post = montar_texto_post_categoria(cat, vagas)
        if not texto_post:
            continue
        run_text = doc.add_paragraph().add_run(texto_post)
        run_text.font.size = Pt(11)

    # Mensagem do PDF no final
    doc.add_paragraph("")
    run_pdf = doc.add_paragraph().add_run(mensagem_pdf)
    run_pdf.font.size = Pt(12)

    doc.save(arquivo_docx)
    print(f"✅ Arquivo Word gerado: {arquivo_docx}")



# ===============================
# 📌 IMPORTAÇÕES E CONFIGURAÇÕES
# ===============================
from oauth2client.service_account import ServiceAccountCredentials
import gspread
import os

from datetime import datetime

def main():

    print("\n>>> MAIN EXECUTADO <<<\n")

    # ===============================
    # 📌 Configurações
    # ===============================
    SHEET_ID = os.getenv("GOOGLE_SHEET_ID", "").strip()
    if not SHEET_ID:
        raise ValueError("Defina GOOGLE_SHEET_ID no arquivo .env (consulte o README).")

    # Service account do Sheets
    if os.path.exists("/content/drive"):
        BASE_PATH = os.getenv("SIDWORKS_BASE_PATH", str(Path(__file__).resolve().parent))
    else:
        # Ambiente GitHub Actions ou outro servidor
        BASE_PATH = os.getenv("SIDWORKS_BASE_PATH", str(Path(__file__).resolve().parent))

    CREDENTIALS_JSON = os.path.join(BASE_PATH, "creds/credentials.json")
    GMAIL_CREDENTIALS_PATH = os.path.join(BASE_PATH, "creds/credentials_gmail.json")

    # Gmail API
    GMAIL_SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
    TOKEN_PATH = os.path.join(BASE_PATH, "creds/token.json")

    # Ajusta fuso horário para São Paulo, com compatibilidade entre sistemas
    if platform.system() != "Windows":  # Linux ou macOS
        os.environ['TZ'] = 'America/Sao_Paulo'
        time.tzset()
    else:
        # No Windows, apenas define a variável de ambiente (tzset não existe)
        os.environ['TZ'] = 'America/Sao_Paulo'
        print("⚠️ Aviso: tzset() não disponível no Windows. Horário local pode estar em UTC.")

    # ===============================
    # 📌 Execução principal
    # ===============================
    # ===============================
    # 📌 Google Sheets Auth (correto)
    # ===============================

    CREDENTIALS_JSON = os.path.join(BASE_PATH, "creds/credentials.json")

    if not os.path.exists(CREDENTIALS_JSON):
        raise FileNotFoundError(f"⚠️ Arquivo de credenciais não encontrado em: {CREDENTIALS_JSON}")

    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_JSON, scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SHEET_ID).sheet1
    spreadsheet = sheet.spreadsheet

    # Inicializa encurtador
    s = pyshorteners.Shortener()

    # Lista de categorias
    categorias = [
        "Dados/BI/Analytics",
        "Desenvolvimento/Sistemas",
        "Estágio/Trainee",
        "Infra/Suporte",
        "Processos/Governança",
        "Demais Vagas",
        "Outros"
    ]

    # Supondo que você já tenha carregado as keywords antes:
    keywords_lookup = carregar_keywords(spreadsheet)

    # 1. Google Alerts
    dados_alerts = []
    for feed_url in RSS_FEEDS:
        feed = feedparser.parse(feed_url)
        for entry in feed.entries:
            titulo = limpar_html(entry.get("title", ""))
            link = limpar_link(entry.get("link", "").strip(), entry)

            # Ignora links de domínios proibidos
            if dominio_esta_blacklistado(link):
                print(f"🔕 Ignorado (domínio bloqueado): {link}")
                continue

            # Tenta extrair URL real se for link do Google
            if link and "google.com" in link:
                cand = extract_first_url(entry.get("summary", ""))
                if cand:
                    link = try_unquote(cand)

            categoria = categorizar_titulo(titulo, keywords_lookup)
            short_link = encurtar_tinyurl(link, timeout=15) if link else ""
            dados_alerts.append([titulo, link, short_link, categoria])

    # =======================================
    # 🔍 2. Controle de ambiente (Gmail/LinkedIn)
    # =======================================

    # 📁 Definir pasta de exportação
    amb = ambiente()

    if amb == "colab":
        PASTA_EXPORTS = os.getenv("SIDWORKS_REPORTS_PATH", "exports")

    elif amb == "actions":
        PASTA_EXPORTS = os.getenv("SIDWORKS_REPORTS_PATH", "exports")
        os.makedirs(PASTA_EXPORTS, exist_ok=True)

    else:
        PASTA_EXPORTS = os.getenv("SIDWORKS_REPORTS_PATH", "exports")
        os.makedirs(PASTA_EXPORTS, exist_ok=True)

    # ================================
    # 🔍 Controle de Gmail / LinkedIn
    # Apenas ambiente LOCAL usa isso
    # ================================
    dados_linkedin = []

    if amb in ["colab", "actions"]:
        print("📭 Ambiente sem navegador → Gmail/LinkedIn DESATIVADOS.")
    else:
        print("📧 Ambiente LOCAL → Gmail/LinkedIn ATIVADOS.")
        oauth_file = os.path.join(BASE_PATH, "creds", "credentials_gmail.json")
        if not os.path.exists(oauth_file):
            print("ℹ️ OAuth Gmail não configurado — usando apenas RSS e links sugeridos.")
            service = None
        else:
            service = gmail_authenticate()

        if service:
            for titulo, link, categoria in get_linkedin_jobs(service, keywords_lookup, max_results=5):
                short_link = encurtar_tinyurl(link, timeout=15)
                dados_linkedin.append([titulo, link, short_link, categoria])
        else:
            print("⚠️ Serviço Gmail indisponível — pulando LinkedIn.")

    # 1️⃣ Normaliza dados dos feeds (Google Alerts + LinkedIn)
    padrao_alerts_linkedin = []
    for t, l, s, c in dados_alerts:
        padrao_alerts_linkedin.append(make_record(t, l, s or l, c, sugerido=False))
    for t, l, s, c in dados_linkedin:
        padrao_alerts_linkedin.append(make_record(t, l, s or l, c, sugerido=False))

    # 2️⃣ Carrega links sugeridos
    links_sugeridos = carregar_links_sugeridos(spreadsheet, keywords_lookup)
    padrao_sugeridos = []
    for s in links_sugeridos:
        titulo = s.get("Vaga") or ""
        # ✅ Adiciona prefixo apenas se ainda não existir
        if titulo and not titulo.startswith("[SUGERIDO]"):
            titulo = f"[SUGERIDO] {titulo}"

        padrao_sugeridos.append(make_record(
            titulo,
            s.get("Link"),
            s.get("Short Link") or s.get("Link"),
            s.get("Categoria", "Outros"),
            sugerido=True
        ))

    # 3️⃣ Junta tudo numa única lista
    todos = padrao_alerts_linkedin + padrao_sugeridos

    # 4️⃣ Deduplicação com priorização dos sugeridos
    vistos = {}
    for rec in todos:
        titulo, link, short_link, categoria, sugerido = rec
        chave = obter_chave_deduplicacao(link or short_link)
        if not chave:
            chave = f"sem-url:{titulo[:80]}"

        if chave in vistos:
            # se o novo registro é sugerido, ele substitui o anterior
            if sugerido and not vistos[chave][4]:
                vistos[chave] = rec
        else:
            vistos[chave] = rec

    # 5️⃣ Gera lista final sem duplicatas
    unicos = list(vistos.values())

    # 6️⃣ Ordena conforme ordem da lista 'categorias'
    categoria_index = {cat.lower(): i for i, cat in enumerate(categorias)}

    def sort_key(rec):
        titulo, link, short_link, categoria, sugerido = rec
        idx = categoria_index.get(categoria.lower(), len(categorias))
        return (idx, (titulo or "").lower(), (link or short_link or "").lower())

    unicos.sort(key=sort_key)

    # 7️⃣ Remove flag sugerido e salva formato esperado
    dados_sem_dup = unicos  # mantém o campo sugerido

    # Atualiza conjunto de chaves únicas
    links_vistos = {obter_chave_deduplicacao(r[1] or r[2]) for r in dados_sem_dup}

    print(f"\n✅ Total final sem duplicatas: {len(dados_sem_dup)} vagas únicas.\n")

    # 🔹 Recarrega lista de abas da planilha
    abas_existentes = [w.title for w in spreadsheet.worksheets()]

    # ===============================
    # 📌 Carregar blacklist
    # ===============================
    if "Blacklist" in abas_existentes:
        aba_blacklist = spreadsheet.worksheet("Blacklist")
        # Pula o cabeçalho e pega a coluna 'Short Link' (índice 2)
        urls_blacklist = set(limpar_link(url[2]) for url in aba_blacklist.get_all_values()[1:])
    else:
        urls_blacklist = set()

    # ===============================
    # 📌 Criar/Atualizar abas separadas por categoria com filtro da blacklist
    # ===============================
    for cat in categorias:
        # Verifica se a aba já existe
        if cat in abas_existentes:
            aba = spreadsheet.worksheet(cat)
            aba.clear()  # limpa conteúdo antigo
        else:
            # Cria a aba apenas se não existir
            aba = spreadsheet.add_worksheet(title=cat, rows=1000, cols=4)
            abas_existentes.append(cat)

        # Filtra os dados da categoria e remove URLs na blacklist
        dados_cat = []
        for row in dados_sem_dup:
            tipos = [t.strip() for t in row[3].split(",")]  # row[3] = categoria
            link_limpo = limpar_link(row[2])  # <--- limpa para comparação
            if cat in tipos and link_limpo not in urls_blacklist:
                dados_cat.append([row[0], row[1], row[2], cat])  # mantém link original para exibição

        # Escreve cabeçalho
        aba.append_row(["Vaga", "Link", "Short Link", "Categoria"], value_input_option="USER_ENTERED")

        # Adiciona dados
        if dados_cat:
            aba.append_rows(dados_cat, value_input_option="USER_ENTERED")

    # 4. Atualizar planilha
    sheet.clear()
    sheet.append_row(["Vaga", "Link", "Short Link", "Categoria"])
    if dados_sem_dup:
        sheet.append_rows([list(row[:4]) for row in dados_sem_dup])
    print(f"\n{len(dados_sem_dup)} vagas atualizadas na planilha.\n")
    from fpdf import FPDF, XPos, YPos
    from datetime import datetime
    import pandas as pd

    # Credenciais e IDs
    #scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"] - #DECLARAÇÃO DUPLICADA


    # ===============================
    # 📌 EXECUÇÃO
    # ===============================
    MIN_VAGAS_POR_POST = 5
    MAX_VAGAS_POR_POST = 5
    SEED_ALEATORIEDADE = None  # defina se quiser reproduzir o mesmo sorteio

    # Gera timestamp para nome dos arquivos
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    base_nome = f"SidWorks TI - {timestamp}"

    # Lê diretamente das abas das categorias, ignorando 'OUTROS'
    vagas_por_cat = obter_vagas_por_aba(spreadsheet, categorias, urls_blacklist=urls_blacklist)

    # Sorteia vagas e mensagens
    amostras = sortear_vagas_por_categoria(vagas_por_cat, MIN_VAGAS_POR_POST, MAX_VAGAS_POR_POST,
                                           seed=SEED_ALEATORIEDADE)
    mensagem_dia = sortear_mensagem_diaria(SEED_ALEATORIEDADE)
    mensagem_pdf = sortear_mensagem_pdf(SEED_ALEATORIEDADE)
    # ===============================
    # 📂 EXPORTAÇÃO DOS ARQUIVOS
    # ===============================
    os.makedirs(PASTA_EXPORTS, exist_ok=True)

    output_pdf = os.path.join(PASTA_EXPORTS, f"{base_nome}.pdf")
    output_docx = os.path.join(PASTA_EXPORTS, f"{base_nome}.docx")
    #output_txt = os.path.join(PASTA_EXPORTS, f"{base_nome}.txt")

    # Gera arquivos
    gerar_pdf_vagas_por_aba(
        spreadsheet,
        categorias,
        urls_blacklist,
        dados_sem_dup=dados_sem_dup,
        base_path=BASE_PATH,
        arquivo_pdf=output_pdf
    )

    gerar_word_com_posts(amostras, mensagem_dia, mensagem_pdf, arquivo_docx=output_docx)

    print("\n✅ Arquivos gerados com sucesso:")
    print(f"📄 PDF:  {output_pdf}")
    print(f"📝 DOCX: {output_docx}")

    # ===============================
    # ☁️ Upload para o Google Drive (universal)
    # ===============================
    try:
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
        from google.auth.transport.requests import Request

        amb = ambiente()

        if amb == "colab":
            TOKEN_GMAIL = os.path.join(os.getenv("SIDWORKS_BASE_PATH", str(Path(__file__).resolve().parent)), "creds/token_gmail.json")
        elif amb == "actions":
            TOKEN_GMAIL = "creds/token_gmail.json"
        else:
            TOKEN_GMAIL = os.path.join(BASE_PATH, "creds/token_gmail.json")

        if not os.path.exists(TOKEN_GMAIL):
            print(f"⚠️ Token Gmail não encontrado ({TOKEN_GMAIL}) — upload para o Drive ignorado.")
            raise FileNotFoundError

        creds = Credentials.from_authorized_user_file(
            TOKEN_GMAIL,
            ["https://www.googleapis.com/auth/gmail.readonly", "https://www.googleapis.com/auth/drive.file"],
        )

        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            Path(TOKEN_GMAIL).write_text(creds.to_json(), encoding="utf-8")

        drive_service = build("drive", "v3", credentials=creds)

        DRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID", "")
        if not DRIVE_FOLDER_ID:
            print("ℹ️ GOOGLE_DRIVE_FOLDER_ID vazio — upload para Drive ignorado.")
            raise ValueError("Pasta Drive não configurada")

        for filepath in [output_pdf, output_docx]:
            if not os.path.exists(filepath):
                print(f"⚠️ Arquivo não encontrado: {filepath}")
                continue

            metadata = {"name": os.path.basename(filepath), "parents": [DRIVE_FOLDER_ID]}
            media = MediaFileUpload(filepath, resumable=True)

            # ✅ Verifica se já existe um arquivo com o mesmo nome na pasta
            query = f"name='{os.path.basename(filepath)}' and '{DRIVE_FOLDER_ID}' in parents and trashed=false"
            results = drive_service.files().list(q=query, fields="files(id)").execute()
            files_found = results.get("files", [])

            if files_found:
                file_id = files_found[0]["id"]
                # Atualiza o arquivo existente
                drive_service.files().update(fileId=file_id, media_body=media).execute()
                print(f"☁️ Atualizado no Drive: {os.path.basename(filepath)}")
            else:
                # Cria novo arquivo
                drive_service.files().create(body=metadata, media_body=media, fields="id").execute()
                print(f"☁️ Enviado para o Drive: {os.path.basename(filepath)}")

    except Exception as e:
        print(f"⚠️ Upload para o Drive não realizado: {e}")

    finally:
        pass

    # ===============================
    # 📎 Download no Colab
    # ===============================
    try:
        from google.colab import files
        print("\n📎 PDF pronto para download ou acesso no Google Drive:")
        print(output_pdf)
    except ImportError:
        print("\n⚠️ Rodando fora do Colab — os arquivos foram salvos localmente.")



def executar_demo(destino=None):
    """Executa um exemplo offline com vagas inventadas, sem acessar Google ou encurtadores."""
    import csv
    raiz = Path(__file__).resolve().parent
    pasta_exemplos = raiz / "examples"
    with (pasta_exemplos / "keywords_exemplo.csv").open(encoding="utf-8-sig", newline="") as f:
        chaves = [
            (normalize_text(r["Keyword"].strip()), r["Categoria"].strip())
            for r in csv.DictReader(f) if r.get("Keyword")
        ]
    registros = []
    with (pasta_exemplos / "vagas_exemplo.csv").open(encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            titulo = r["Vaga"].strip()
            link = limpar_link(r["Link"].strip())
            categoria = categorizar_titulo(titulo, chaves)
            registros.append([titulo, link, link, categoria])
    registros = deduplicar_vagas(registros)
    dados = [make_record(t, l, sl, c, sugerido=False) for t, l, sl, c in registros]
    categorias = ["Dados/BI/Analytics", "Desenvolvimento/Sistemas", "Estágio/Trainee",
                  "Infra/Suporte", "Processos/Governança", "Outros"]
    destino = Path(destino) if destino is not None else raiz / "exports"
    destino.mkdir(parents=True, exist_ok=True)
    arquivo_pdf = destino / "SidWorksTI_Demonstracao.pdf"
    arquivo_word = destino / "SidWorksTI_Demonstracao_WhatsApp.docx"
    gerar_pdf_vagas_por_aba(
        None, categorias, dados_sem_dup=dados, base_path=str(raiz),
        arquivo_pdf=str(arquivo_pdf), modo_demo=True
    )
    amostras = {}
    for cat in categorias:
        grupo = []
        for titulo, link, short, categoria, _ in dados:
            if cat in [p.strip() for p in categoria.split(",")]:
                grupo.append({"vaga": titulo, "link": link, "short_link": short})
        if grupo:
            amostras[cat] = grupo
    gerar_word_com_posts(
        amostras,
        mensagem_dia="DEMONSTRAÇÃO — VAGAS FICTÍCIAS (NÃO DIVULGAR COMO REAIS)",
        mensagem_pdf="PDF com vagas de demonstração gerado localmente.",
        arquivo_docx=str(arquivo_word),
        titulo_documento="SidWorks TI — Demonstração Offline"
    )
    print(f"\n✅ Demonstração finalizada: {len(dados)} oportunidades fictícias únicas")
    print(f"📄 {arquivo_pdf}\n📝 {arquivo_word}")
    return dados

# Proteção simples contra duas execuções simultâneas.
# O arquivo é removido também em caso de erro.
def executar_com_bloqueio():
    try:
        fd = os.open(LOCK_FILE, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        raise SystemExit("Execução bloqueada: arquivo .sidworks_execucao já existe.")
    else:
        os.close(fd)
    try:
        main()
    finally:
        try:
            os.unlink(LOCK_FILE)
        except FileNotFoundError:
            pass


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "--demo":
        executar_demo()
    elif len(sys.argv) == 1:
        executar_com_bloqueio()
    else:
        raise SystemExit("Uso: python main.py [--demo]")
