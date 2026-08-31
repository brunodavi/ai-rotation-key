import logging
import sys
import unittest

from src.utils.logging_setup import setup_logging


class SetupLoggingTests(unittest.TestCase):
    def setUp(self):
        self.root = logging.getLogger("airkey")
        self.original_level = self.root.level
        self.original_handlers = self.root.handlers[:]

    def tearDown(self):
        self.root.setLevel(self.original_level)
        self.root.handlers = self.original_handlers

    def test_setup_logging_default_level_is_info(self):
        setup_logging()
        self.assertEqual(self.root.level, logging.INFO)

    def test_setup_logging_verbose_0_means_no_debug(self):
        setup_logging(verbose=0)
        self.assertFalse(self.root.isEnabledFor(logging.DEBUG))

    def test_setup_logging_verbose_1_enables_debug(self):
        setup_logging(verbose=1)
        self.assertTrue(self.root.isEnabledFor(logging.DEBUG))

    def test_setup_logging_handler_writes_to_stdout(self):
        setup_logging()
        handler = self.root.handlers[-1]
        self.assertIsInstance(handler, logging.StreamHandler)
        self.assertIs(handler.stream, sys.stdout)

    def test_setup_logging_does_not_add_duplicate_handlers(self):
        initial = len(self.root.handlers)
        setup_logging()
        setup_logging()
        self.assertEqual(len(self.root.handlers), initial + 1)

    def test_log_message_suppressed(self):
        setup_logging()
        logger = logging.getLogger("airkey.test")
        logger.info("should not raise")
