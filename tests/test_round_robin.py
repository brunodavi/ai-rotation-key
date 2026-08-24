import threading
import unittest

from src.utils.round_robin import RoundRobin


class RoundRobinTests(unittest.TestCase):
    def setUp(self):
        self.rr = RoundRobin(
            {
                "m-tres": ["sk-a", "sk-b", "sk-c"],
                "m-um": ["sk-unica"],
            }
        )

    def test_cicla_na_ordem_da_lista(self):
        sequencia = [self.rr.next("m-tres") for _ in range(6)]
        self.assertEqual(sequencia, ["sk-a", "sk-b", "sk-c", "sk-a", "sk-b", "sk-c"])

    def test_cursores_independentes_por_modelo(self):
        primeiro_m_tres = self.rr.next("m-tres")
        self.rr.next("m-um")
        self.rr.next("m-um")
        proximo_m_tres = self.rr.next("m-tres")
        self.assertEqual(primeiro_m_tres, "sk-a")
        self.assertEqual(proximo_m_tres, "sk-b")

    def test_modelo_desconhecido_levanta_key_error_com_nome(self):
        with self.assertRaises(KeyError) as ctx:
            self.rr.next("nao-existe")
        self.assertIn("nao-existe", str(ctx.exception))

    def test_modelo_de_chave_unica_sempre_devolve_a_mesma(self):
        for _ in range(4):
            self.assertEqual(self.rr.next("m-um"), "sk-unica")

    def test_thread_safety_multiset_deterministico(self):
        pool = ["sk-a", "sk-b", "sk-c"]
        total_por_thread = 200
        threads = 8
        resultados = []
        lock = threading.Lock()

        def consumir():
            locais = [self.rr.next("m-tres") for _ in range(total_por_thread)]
            with lock:
                resultados.extend(locais)

        workers = [threading.Thread(target=consumir) for _ in range(threads)]
        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join()

        total = threads * total_por_thread
        self.assertEqual(len(resultados), total)
        self.assertTrue(set(resultados).issubset(set(pool)))
        esperado = total // len(pool)
        sobra = total % len(pool)
        for chave in pool:
            contagem = resultados.count(chave)
            self.assertIn(contagem, {esperado, esperado + (1 if sobra else 0)})

    def test_construtor_rejeita_modelo_sem_chaves(self):
        with self.assertRaises(ValueError):
            RoundRobin({"vazio": []})


if __name__ == "__main__":
    unittest.main()
