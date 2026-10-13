"""Verificações locais do pacote de distribuição."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class PublicacaoSegura(unittest.TestCase):
    def test_fontes_necessarias_e_licenca(self):
        for nome in ('DejaVuSans.ttf', 'DejaVuSans-Bold.ttf', 'DejaVuSans-Oblique.ttf', 'LICENSE-DejaVu.txt'):
            self.assertTrue((ROOT / 'fonts' / nome).exists(), nome)

    def test_sem_link_ficticio_fixo_nos_relatorios(self):
        codigo = (ROOT / 'main.py').read_text(encoding='utf-8')
        self.assertNotIn('whatsapp.com/channel/SEU_CANAL', codigo)
        self.assertIn('WHATSAPP_CHANNEL_URL', codigo)

    def test_token_json_em_vez_de_pickle(self):
        codigo = (ROOT / 'main.py').read_text(encoding='utf-8')
        self.assertNotIn('pickle.load(', codigo)
        self.assertIn('Credentials.from_authorized_user_file', codigo)

if __name__ == '__main__':
    unittest.main()
