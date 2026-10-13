"""Teste de demonstração sem rede ou conta Google."""
import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch
import main


class DemoOffline(unittest.TestCase):
    def test_demo_nao_usa_apis_remotas_e_gera_documentos(self):
        # Cada teste grava em um diretório isolado: não sobrescreve exports/.
        with tempfile.TemporaryDirectory(prefix="sidworks-test-") as pasta_temporaria:
            pasta = Path(pasta_temporaria)
            with patch.object(main.requests, "get", side_effect=AssertionError("Rede não permitida")):
                vagas = main.executar_demo(destino=pasta)
            self.assertEqual(len(vagas), 5)
            self.assertGreater((pasta / "SidWorksTI_Demonstracao.pdf").stat().st_size, 1000)
            self.assertGreater((pasta / "SidWorksTI_Demonstracao_WhatsApp.docx").stat().st_size, 1000)
