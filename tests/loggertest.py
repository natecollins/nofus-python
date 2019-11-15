import os
import unittest
import re
import time
from nofus import Logger, LoggingInterface

MEMLOGS = []

class CustomLogger(LoggingInterface):
    def __init__(self, log_file=None, log_level=None):
        if log_level is None:
            log_level = Logger.LOG_LOW
        self.log_file = log_file
        self.log_level = log_level

    def make_log(self, entry, log_level):
        global MEMLOGS
        if (self.log_level & log_level) != Logger.LOG_NONE:
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            level = "CUSTOM"
            if log_level == Logger.LOG_CRITICAL:
                level = "CRITICAL"
            elif log_level == Logger.LOG_ERROR:
                level = "ERROR"
            elif log_level == Logger.LOG_WARNING:
                level = "WARNING"
            elif log_level == Logger.LOG_NOTICE:
                level = "NOTICE"
            elif log_level == Logger.LOG_INFO:
                level = "INFO"
            elif log_level == Logger.LOG_DEBUG:
                level = "DEBUG"
            elif log_level == Logger.LOG_TRACE:
                level = "TRACE"

            entry = "[{0}] {1}".format(level, entry)
            MEMLOGS.append(entry)

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

        valid_log = "[TS] [DEBUG] Debug!" + os.linesep + \
                    "[TS] [INFO] Info!" + os.linesep + \
                    "[TS] [NOTICE] Notice!" + os.linesep + \
                    "[TS] [WARNING] Warning!" + os.linesep + \
                    "[TS] [ERROR] Error!" + os.linesep + \
                    "[TS] [CRITICAL] Critical!" + os.linesep

        log_content = ""
        with open(self.log_file, 'r') as logread:
            log_content = logread.read(1024)
        log_content = re.sub('^\[[^[]+\]',"[TS]", log_content)
        log_content = re.sub(os.linesep + '\[[^[]+\]', os.linesep + "[TS]", log_content)
        self.assertIsNotNone(log_content)
        self.assertEqual(valid_log, log_content)

    def test_custom_logger(self):
        Logger.register(CustomLogger())
        Logger.trace("Trace!");
        Logger.debug("Debug!");
        Logger.info("Info!");
        Logger.notice("Notice!");
        Logger.warning("Warning!");
        Logger.error("Error!");
        Logger.critical("Critical!");

        self.assertEqual(2, len(MEMLOGS));
        self.assertEqual("[ERROR] Error!", MEMLOGS[0]);
        self.assertEqual("[CRITICAL] Critical!", MEMLOGS[1]);

