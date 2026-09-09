import unittest

import src.utils


class BarrelTests(unittest.TestCase):
    def test_barrel_e_vazio_de_proposito(self):
        self.assertFalse(hasattr(src.utils, "__all__"))


if __name__ == "__main__":
    unittest.main()
