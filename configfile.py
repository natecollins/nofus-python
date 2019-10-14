"""
NOFUS Config File Parser for Python

****************************************************************************************
Copyright 2014 Nathan Collins. All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are
permitted provided that the following conditions are met:

   1. Redistributions of source code must retain the above copyright notice, this list of
      conditions and the following disclaimer.

   2. Redistributions in binary form must reproduce the above copyright notice, this list
      of conditions and the following disclaimer in the documentation and/or other materials
      provided with the distribution.

THIS SOFTWARE IS PROVIDED BY Nathan Collins ``AS IS'' AND ANY EXPRESS OR IMPLIED
WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND
FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL Nathan Collins OR
CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

The views and conclusions contained in the software and documentation are those of the
authors and should not be interpreted as representing official policies, either expressed
or implied, of Nathan Collins.

*****************************************************************************************

****************************************
* Config file line examples
****************************************

# Pound sign is a line comment
# Variable assignment is done with an "=" sign
var1 = 42
var2 = 94                                           # comments can appear at the end of a line
name = Example
longname = John Doe                                 # would parse as "John Doe"
name2 = " Jane Doe "                                # to prevent whitespace trimming, add double quotes; would parse as " Jane Doe "
name3 = 'Jerry'                                     # single quotes parse as normal characters; would parse as "'Jerry'"
words = "Quotes \"inside\" a string"                # can use double quotes inside double quotes, but must be escaped
specials = "This has #, \\, and = inside of it"     # can use special characters in a quoted value (escape character must be escaped)
badquoted = this is "NOT" a quoted string           # value doesn't start with a quote, so quotes are treated as normal chars
oddquote = "not a quoted value" cause extra         # value will parse as: "\"not a quoted value\" cause extra"
novalue =                                           # values can be left blank
enable_keys                                         # no assignment delimiter given (aka '='), variable is assigned boolean value true
multi_valued = abc
multi_valued = xyz                                  # variables can be defined multiple times and retrieved as an array

// Alternate line comment style

# variables can have a scope by placing a dot in their identifier
marbles.green = 2
marbles.blue = 4
marbles.red = 3

# alternatively, you can set scope on variables by making a section using []
[marbles]
white = 6
clear = 8
yellow = 1

[sql.maria]                         # scopes can have sub-scopes as well (and comments)
auth.server = sql.example.com
auth.user = apache                  # e.g. full scope is: sql.maria.auth.user
auth.pw = secure
auth.db = website

 **************************************
 * Invalid examples
 **************************************

my var = my val         # spaces are not allowed in variable identifiers
[]#.$ = something       # only a-zA-Z0-9_- are allow for variable identifier (. is allowed for scope)
[my.scope]  = val       # scopes cannot have values
a..b = c                # scopes cannot be blank
.d. = e                 # start and end scope can't be blank


 **************************************
 * Use examples
 **************************************

$cf = new ConfigFile("test.conf");
if ($cf->load()) {
    # can preload default values, even after loading
    $cf->preload(
        array(
            "var1"=>12,
            "name"=>"none",
            "enable_keys"=>false,
            "marbles.green"=>0
        )
    );

    $v1 = $cf->get("var1");         # get value from var1, or null if doesn't exist
    $v9 = $cf->get("var9", 123);    # get value from var9, or 123 if doesn't exist

    $arr = $cf->getArray("multi_valued");   # get all values for multi_valued as an array

    $mw = $cf->get("marbles.white", 1);     # get marbles.white, or 1 if doesn't exist
    $pw = $cf->get("sql.maria.auth.pw");    # get sql.maria.auth.pw, or null if doesn't exist

    $sql = $cf->get('sql.maria');           # get a scope
    $svr = $sql->get('auth.server');        # get auth.server (from sql.maria scope), or null if doesn't exist

    $bad = $cf->get('does.not.exist');      # attempt to get a non-existant scope, returns null

    $sub_scopes = $cf->enumerateScope("sql.maria.auth"); # returns array of ['server','user','pw','db']
"""
from collections import Mapping


class ConfigFile:
    """
    The main ConfigFile class
    """
    def __init__(self, file_to_open):
        # File Info
        self.file_path = None
        self.loaded = False

        # Static parse values
        self.line_comment_start = ['#', '//']
        self.var_val_delimiter = '='
        self.scope_delimiter = '.'
        self.quote_char = '\"'
        self.escape_char = '\\'
        self.scope_char_set = "a-zA-Z0-9_\-"
        self.varname_char_set = "a-zA-Z0-9_\-"

        # Dynamic parse values
        self.current_scope = ""

        # Errors
        self.errors = []

        # Parsed Content
        self.values = {}

        # Parse file_to_open
        if file_to_open is not None and isinstance(file_to_open, str):
            file_path = file_to_open

    def _override_comment_starts(self, line_comment_start):
        """
        Change what strings indicate the start of a comment.
        WARNING: Change this at your own risk. Setting unusual values here may break parsing.
        :type list_or_string: Union[list, string]
        :param line_comment_start list_or_string
                An array containing strings which indicate the start of a comment
                OR a string that indicates the start of a comment
        """
        if type(line_comment_start) is not list and isinstance(line_comment_start, str):
            self.line_comment_start = [line_comment_start]
        self.line_comment_start = line_comment_start

    def _override_variable_delimiter(self, var_val_delimiter):
        """
        Change the delimiter used between variable name and values.
        WARNING: Change this at your own risk. Setting unusual values here may break parsing.
        :param var_val_delimiter string The string to indicate the delimiter between variable name and value
        """
        self.var_val_delimiter = var_val_delimiter

    def _override_scope_delimiter(self, scope_delimiter):
        """
        Change the string used as a delimiter between scopes.
        WARNING: Change this at your own risk. Setting unusual values here may break parsing.
        :param scope_delimilte string The string to indicate the delimiter between scopes
        """
        self.scope_delimilter = scope_delimiter

    def _override_quote_character(self, quote_char):
        """
        Change the character used to quote variable values.
        WARNING: Change this at your own risk. Setting unusual values here may break parsing.
        :param quote_char string The character to indicate the start and end of a quoted value
        """
        self.quote_char = quote_char

    def _override_escape_character(self, escape_char):
        """
        Change the character used to escape other characters in a variable value
        WARNING: Change this at your own risk. Setting unusual values here may break parsing.
        :param escape_char string The character to indicate an excaped character follows
        """
        self.escape_char = escape_char

    def _override_scope_characters(self, scope_char_set):
        """
        Change the regular expression patterned used to verify valid scope names.
        WARNING: Change this at your own risk. Setting unusual values here may break parsing.
        :param scope_char_set string A regexp patterns to indicate allowed characters in a scope name
        """
        self.scope_char_set = scope_char_set

    def _override_variable_name_characters(self, varname_char_set):
        """
        Change the regular expression patterned used to verify valid variable names.
        WARNING: Change this at your own risk. Setting unusual values here may break parsing.
        :param varname_char_set string A regexp patterns to indicate allowed characters in a variable name
        """
        self.varname_char_set = varname_char_set

    def preload(self, defaults):
        """
        Load in default values for certain variables/scopes. If a variable already
        exists (e.g. from a file that was already loaded), then this will NOT overwrite
        the value.
        :param defaults dict A dictionary of "scope.variable": "default value" pairs
                         OR dict value may also be another dict of values
        """
        for name, value in defaults.items():
            if not name in self.values:
                if isinstance(value, (list, Mapping)):
                    self.values[name] = value
                else
                    self.values[name] = [value]

    def reset(self):
        """
        Reset the config file object, basically "unloading" everything so it can be reloaded.
        """
        self.loaded = False
        self.errors = []
        self.values = {}
