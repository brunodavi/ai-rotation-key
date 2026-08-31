import logging
import sys
import unittest

from src.utils.logging_setup import KEYFULL, KEYMASKED, setup_logging


class SetupLoggingTests(unittest.TestCase):
    def setUp(self):
        self.root = logging.getLogger("airkey")
        self.original_level = self.root.level
        self.original_handlers = self.root.handlers[:]

    def tearDown(self):
        self.root.setLevel(self.original_level)
        self.root.handlers = self.original_handlers

    def test_verbose_0_sets_info_level(self):
        setup_logging(verbose=0)
        self.assertEqual(self.root.level, logging.INFO)

    def test_verbose_0_hides_debug(self):
        setup_logging(verbose=0)
        self.assertFalse(self.root.isEnabledFor(logging.DEBUG))

    def test_verbose_1_sets_debug_level(self):
        setup_logging(verbose=1)
        self.assertEqual(self.root.level, logging.DEBUG)

    def test_verbose_1_enables_debug(self):
        setup_logging(verbose=1)
        self.assertTrue(self.root.isEnabledFor(logging.DEBUG))

    def test_verbose_2_sets_keymasked_level(self):
        setup_logging(verbose=2)
        self.assertEqual(self.root.level, KEYMASKED)

    def test_verbose_3_sets_keyfull_level(self):
        setup_logging(verbose=3)
        self.assertEqual(self.root.level, KEYFULL)

    def test_handler_writes_to_stdout(self):
        setup_logging()
        handler = self.root.handlers[-1]
        self.assertIsInstance(handler, logging.StreamHandler)
        self.assertIs(handler.stream, sys.stdout)

    def test_does_not_add_duplicate_handlers(self):
        initial = len(self.root.handlers)
        setup_logging()
        setup_logging()
        self.assertEqual(len(self.root.handlers), initial + 1)

    def test_log_message_suppressed(self):
        setup_logging()
        logger = logging.getLogger("airkey.test")
        logger.info("should not raise")
