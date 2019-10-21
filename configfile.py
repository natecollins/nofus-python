"""
****************************************************************************************
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
import os
import re
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
        :param scope_delimiter string The string to indicate the delimiter between scopes
        """
        self.scope_delimiter = scope_delimiter

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

    def load(self):
        """
        Attempt to open and parse the config file.
        :returns boolean True if the file loaded without errors, false otherwise
        """
        # If we've successfully loaded this file before, skip the load and return success
        if self.loaded == True:
            return True

        # If file is null, then this is a scope query result, do nothing
        if self.file_path is None:
            self.errors.append("Cannot load file; no file was given. (Note: you cannot load() a query result.)")
            return False

        if os.is_file(self.file_path) and os.access(self.file_path, os.R_OK):
            self.errors.append("Cannot load file; file does not exist or is not readable.")
            return False

        lines = []
        try:
            with open(self.file_path) as cfile:
                lines = cfile.readlines()
        except OSError:
            self.errors.append("Cannot load file; unknown file error.")
        lines = [line.rstrip('\r\n') for line in lines]

        # Process lines
        for line_num, line in enumerate(lines):
            self.process_line(line_num, line)

        # If parsing lines generated errors, return false
        if len(self.errors) > 0:
            return False

        # Make it past all error conditions, so return true
        self.loaded = True
        return True

    def find_line_comment_position(self, line, search_offset=0):
        """
        Find the position of the first line comment (ignoring all other rules)
        :param line string The line to search over
        :param search_offset int Offset from start of line in characters to skip before searching
        :returns int|false The position of line comment start, or false if no line comment was found
        """
        start = False
        for comment_start in self.line_comment_start:
            start_check = line.find(comment_start, search_offset)
            if start_check != -1 and (start == False or start_check < start):
                start = start_check

        return start

    def find_assignment_delimiter_position(self, line):
        """
        Find the position of the first assignment delimiter (ignoring all other rules)
        :param line string The line to search over
        :returns int|false The position of the assignment delimiter, or false if no delimiter was found
        """
        pos = line.find(line, self.var_val_delimiter)
        return pos if pos != -1 else False

    def find_open_quote_position(self, line):
        """
        Find the position of the opening double quote character (ignoring all other rules)
        :param line string The line to search over
        :returns int|false The position of the double quote, or false is not found
        """
        pos = line.find(line, self.quote_char)
        return pos if pos != -1 else False

    def is_valid_scope_definition(self, line):
        """
        Given a line, check to see if it is a valid scope definition
        :param line string The line to check
        :return boolean Returns true if well formed and valid, false otherwise
        """
        valid_char_set = self.scope_char_set
        scope_char = re.escape(self.scope_delimiter)
        esc_comment_starts = ''
        for comment_start as self.line_comment_start:
            if esc_comment_starts != '':
                esc_comment_starts += '|'
            esc_comment_starts += re.escape(comment_start)

        scope_pattern = "^\s*\[\s*(?:[{0}]+(?:{1}[{0}]+)*)?\s*\]\s*(?:({2}).*)?$".format(valid_char_set, scope_char, esc_comment_starts)

        # default to not a scope
        valid = False
        # check for validity
        patt = re.compile(scope_pattern)
        if patt.search(line):
            valid = True

        return valid

    def set_scope(self, line):
        """
        Set the current scope (assumes the line is a scope definition) while parsing the file. Does nothing if line is not a scope definition.
        :param line string The line to get the scope from
        """
        valid_char_set = self.scope_char_set
        scope_char = re.escape(self.scope_delimiter)
        esc_comment_starts = ''
        for comment_start in self.line_comment_start:
            if esc_comment_starts != '':
                esc_comment_starts += '|'
            esc_comment_starts += re.escape(comment_start)

        scope_pattern = "^\s*\[\s*([{0}]+(?:{1}[{0}]+)*)?\s*\]\s*(?:({2}).*)?$".format(valid_char_set, scope_char, esc_comment_starts)

        # check for invalid characters
        patt = re.compile(scope_pattern)
        match = patt.search(line)
        if match:
            self.current_scope = match.group(1)

    def has_value_delimiter(self, line):
        """
        Check if line has a value delimiter. Can only return true if the line
        also has a valid variable name.
        :param line string The line to check against
        :returns boolean Returns true if line has a delimiter after a valid variable name
        """
        has_delim = False
        if self.has_valid_variable_name(line):
            esc_delim = re.escape(self.var_val_delimiter)
            delim_pattern = re.compile('^[^{0}]+{0}'.format(esc_delim))
            match = re.search(delim_pattern, line)
            if match:
                has_delim = True

        return has_delim

    def has_quoted_value(self, line, line_for_error=None):
        """
        Checks if the line has a valid quoted value.
        :param line string $sLine The line to check
        :param line_for_error int|none If a line number is provided, will add error messages if invalidly quoted
        :return boolean Returns true if a quoted value exist, false otherwise
        """
        #################################################
        # - Variable name must be valid
        # - Assignment delimiter must exist after variable name (allowing for whitespace)
        # - First character after assignment delimiter must be a quote (allowing for whitespace)
        # - Assignment delimiter and open quote must not be in a comment
        # - A matching quote character must exist to close the value
        # - The closing quote has no other chars are after it (other than whitespace and comments)
        #################################################
        quoted_value = False
        if self.has_valid_variable_name(line):
            esc_delim = re.escape(self.var_val_delimiter)
            esc_quote = re.escape(self.quote_char)
            esc_escape = re.escape(self.escape_char)
            esc_comment_starts = ""

            for comment_start in self.line_comment_start:
                if esc_comment_starts != '':
                    esc_comment_starts += '|'
                esc_comment_starts += re.escape(comment_start)

            quote_val_patterns = re.compile("^[^{0}]+{0}\s*{1}(?:{2}{1}|[^{0}])*(?<!{2}){1}\s*(?:({3}).*)?$".format(esc_delim, esc_quote, esc_escape, esc_comment_starts))

            match = quote_val_patterns.search(line)
            if match:
                quoted_value = True

        return quoted_value

    def get_quoted_value(self, line):
        """
        Returns the content from inside a properly quoted value string given a whole line.
        The content from inside the string may still have escaped values.
        :param line string The line to operate from
        :return string The value between the openening and closed quote of the value (does NOT include open/closing quotes); on failure, returns empty string.
        """
        value = ""
        if self.has_valid_variable_name(line):
            esc_delim = re.escape(self.var_val_delimiter)
            esc_quote = re.escape(self.quote_char)
            esc_escape = re.escape(self.escape_char)
            esc_comment_starts = ""

            for comment_start in self.line_comment_start:
                if esc_comment_starts != '':
                    esc_comment_starts += '|'
                esc_comment_starts += re.escape(comment_start)

            quote_val_pattern = "^[^{0}]+{0}\s*{1}((?:{2}{1}|[^{1}])*)(?<!{2}){1}\s*(?:({3}).*)?$".format(esc_delim, esc_quote, esc_escape, esc_comment_starts)

            match = quote_val_patterns.search(line)
            if match:
                value = match.group(1)

        return value

    def get_variable_value(self, line, line_for_error=None):
        """
        Get the processed value for the given line. Handles quotes, comments, and unescaping characters.
        :param line string The line to operate from
        :param line_for_error int|null If a line number is provided, will add error messages if invalidly quoted
        :return string The value processed variable value
        """
        value = False
        if self.has_valid_variable_name(line):
            value = True
            if self.has_value_delimiter(line):
                value = ""
                if self.has_quoted_value(line, line_for_error):
                    # getting the quoted value will strip off comments automatically
                    value = self.get_quoted_value
                else:
                    value = self.get_post_delimiter(line)
                    # handle comments
                    comment_start = self.find_line_comment_position(value)
                    if comment_start != False:
                        value = value[0:comment_start]
                    value = value.strip()

                # handle escaped chars
                esc_escape = re.compile(self.escape_char)
                unescape_pattern = re.compile("{0}(.)".format(esc_escape)
                unescape_replace = "\\1"
                value = re.sub(unescape_pattern, unescape_replace, value)

        return value

