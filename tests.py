import unittest
import os
from configfile import ConfigFile

class ConfigFileTestCase(unittest.TestCase):
    def setUp(self):
        self.test1_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), "test1.conf")

    def test_can_load_file(self):
        cf = ConfigFile(self.test1_file)
        self.assertIsInstance(cf, ConfigFile)
        loaded = cf.load()
        if not loaded:
            for error in cf.errors:
                print(" >> {0}".format(error))
        self.assertTrue(loaded)

    def test_can_parse_all_values(self):
        cf = ConfigFile(self.test1_file)
        cf.load()
        self.assertIsNone(cf.get('badvar1'))
        self.assertIsNone(cf.get('badvar2'))
        self.assertEqual(       'default val',                              cf.get('invalid.var', 'default val'))


if __name__ == '__main__':
    unittest.main()

