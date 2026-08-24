import unittest
from unittest import mock


class MainEntryTests(unittest.TestCase):
    def test_entry_chama_cli_e_nao_propaga_retorno(self):
        import main as entry

        sentinela = ("caminho", True)
        with mock.patch("src.cli.main", return_value=sentinela) as cli_main:
            self.assertIsNone(entry.main())
            cli_main.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
