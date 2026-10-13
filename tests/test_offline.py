"""Testes de lógica local, sem serviços externos ou credenciais."""
import unittest
from pathlib import Path

import main


class TestesOffline(unittest.TestCase):
    def test_importacao_nao_cria_lock(self):
        self.assertFalse(Path(main.LOCK_FILE).exists())

    def test_normalizacao(self):
        self.assertEqual(main.normalize_text("Análise de DADOS"), "analise de dados")

    def test_classificacao(self):
        chaves = [("python", "Desenvolvimento/Sistemas")]
        self.assertEqual(main.categorizar_titulo("Vaga PYTHON", chaves), "Desenvolvimento/Sistemas")
        self.assertEqual(main.categorizar_titulo("Outra oportunidade", chaves), "Outros")

    def test_url_linkedin(self):
        self.assertEqual(main.limpar_link("https://www.linkedin.com/jobs/view/123456789/?trackingId=abc"),
                         "https://www.linkedin.com/jobs/view/123456789/")

    def test_deduplicacao(self):
        vagas = [
            ["Uma vaga", "https://www.linkedin.com/jobs/view/1234/?a=b", "", "Outros"],
            ["Mesma vaga", "https://www.linkedin.com/jobs/view/1234/", "", "Outros"],
            ["Outra vaga", "https://www.linkedin.com/jobs/view/5678/", "", "Outros"],
        ]
        self.assertEqual(len(main.deduplicar_vagas(vagas)), 2)


if __name__ == "__main__":
    unittest.main()
