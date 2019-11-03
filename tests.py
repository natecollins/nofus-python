#!/usr/bin/env python3
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
        self.assertEqual(       '42',                                       cf.get('var1'))
        self.assertEqual(       ['92'],                                     cf.get_array('var2'))
        self.assertEqual(       '92',                                       cf.get('var2'))
        self.assertEqual(       'a string',                                 cf.get('var_3'))
        self.assertEqual(       'quoted string',                            cf.get('VAR-4'))
        self.assertEqual(       'Mis "quoted" string',                      cf.get('_VAR5_'))
        self.assertEqual(       'techinally valid var name',                cf.get('-'))
        self.assertEqual(       'also valid var name',                      cf.get('_'))
        self.assertEqual(       'Yet another  valid name',                  cf.get('99'))
        self.assertEqual(       '  spaced val  ',                           cf.get('var6'))
        self.assertEqual(       '"quoted quotes"',                          cf.get('var7'))
        self.assertEqual(       'quoted string # in value',                 cf.get('var8'))
        self.assertEqual(       '"start quoted" but not ended',             cf.get('var9'))
        self.assertEqual(       'special chars # \\\\ = inside string',     cf.get('var10'))
        self.assertEqual(       '',                                         cf.get('var11'))
        self.assertTrue(         cf.get('var12'))
        self.assertEqual(       'abc',                                      cf.get('multi-var13'))
        self.assertEqual(       ['abc','pqr','xyz'],                        cf.get_array('multi-var13'))
        self.assertEqual(       'non quoted start with "quoted end"',       cf.get('var14'))
        self.assertEqual(       '2',                                        cf.get('marbles.green'))
        self.assertEqual(       '6',                                        cf.get('marbles.white'))
        self.assertEqual(       '1',                                        cf.get('marbles.yellow'))
        cf_marbles = cf.get('marbles')
        self.assertEqual(       '4',                                        cf_marbles.get('blue'))
        self.assertEqual(       '3',                                        cf_marbles.get('red'))
        self.assertEqual(       '8',                                        cf_marbles.get('clear'))
        self.assertIsNone(      cf.get('scope'))
        self.assertEqual(       ['db', 'pw', 'server', 'user'],             sorted(cf.enumerate_scope('sql.maria.auth')))
        cf_auth = cf.get('sql.maria.auth')
        self.assertEqual(       ['db', 'pw', 'server', 'user'],             sorted(cf_auth.enumerate_scope()))
        self.assertEqual(       'sql.example.com',                          cf_auth.get('server'))
        self.assertEqual(       'apache',                                   cf_auth.get('user'))
        self.assertEqual(       'secure',                                   cf.get('sql.maria.auth.pw'))
        cf_maria = cf.get('sql.maria')
        self.assertEqual(       'website',                                  cf_maria.get('auth.db'))
        self.assertEqual(       'a thing',                                  cf.get('var15'))
        self.assertEqual(       'white space before var',                   cf.get('var16'))
        self.assertIsNone(      cf.get('same'))

        self.assertIsInstance(  cf.get_array('invalid.name'),                list)
        self.assertCountEqual(  cf.get_array('invalid.name'),                [])


if __name__ == '__main__':
    unittest.main()

