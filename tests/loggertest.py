import os
import unittest
import re
from logger import Logger

class LoggerTestCase(unittest.TestCase):
    def setUp(self):
        self.log_file = '/tmp/.nofus_test.log'
        if os.path.exists(self.log_file):
            os.unlink(self.log_file)

    def tearDown(self):
        if os.path.exists(self.log_file):
            os.unlink(self.log_file)

    def test_default_logger(self):
        Logger.initialize(self.log_file)
        Logger.trace("Trace!")
        Logger.debug("Debug!")
        Logger.info("Info!")
        Logger.notice("Notice!")
        Logger.warning("Warning!")
        Logger.error("Error!")
        Logger.critical("Critical!")

        self.assertTrue(Logger.is_enabled(Logger.LOG_WARNING))
        self.assertFalse(Logger.is_enabled(Logger.LOG_TRACE))

        Logger.disable()
        Logger.critical("Disabled logs.")
        self.assertIsNone(Logger.is_enabled(Logger.LOG_NOTICE))

        valid_log = "[TS] [DEBUG] Debug!\n" + \
                    "[TS] [INFO] Info!\n" + \
                    "[TS] [NOTICE] Notice!\n" + \
                    "[TS] [WARNING] Warning!\n" + \
                    "[TS] [ERROR] Error!\n" + \
                    "[TS] [CRITICAL] Critical!\n"

        log_content = ""
        with open(self.log_file, 'r') as logread:
            log_content = logread.read(2048)
        log_content = re.sub('^\[[^[]+\]',"[TS]", log_content)
        log_content = re.sub('\n\[[^[]+\]',"\n[TS]", log_content)
        self.assertIsNotNone(log_content)
        self.assertEqual(valid_log, log_content)

    def test_custom_logger(self):
        pass


