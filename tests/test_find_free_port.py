import os
import unittest

from src.utils.find_free_port import find_free_port


class FindFreePortTests(unittest.TestCase):
    def test_porta_livre_devolve_a_preferida(self):
        self.assertEqual(find_free_port(28980), 28980)

    def test_porta_ocupada_cai_para_proxima(self):
        import socket

        bloqueio = socket.socket()
        bloqueio.bind(("", 28981))
        bloqueio.listen(1)
        try:
            self.assertEqual(find_free_port(28981), 28982)
        finally:
            bloqueio.close()

    def test_varias_ocupadas_consecutivas_pula_ate_livre(self):
        import socket

        sockets = []
        for porta in (28983, 28984, 28985):
            s = socket.socket()
            s.bind(("", porta))
            s.listen(1)
            sockets.append(s)
        try:
            self.assertEqual(find_free_port(28983), 28986)
        finally:
            for s in sockets:
                s.close()


if __name__ == "__main__":
    unittest.main()
