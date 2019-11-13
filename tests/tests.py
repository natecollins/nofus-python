#!/usr/bin/env python3
import sys
import unittest
import os
TOP_PATH = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.append(TOP_PATH)
from configfiletest import ConfigFileTestCase
from loggertest import LoggerTestCase

if __name__ == '__main__':
    unittest.main()

