'''
A wrapper class for MariaDB connections.
'''
import sys
import mariadb
import re
import html
from functools import cache
from io import StringIO
from typing import Any, Dict, List, Optional, Tuple, Union
from enum import Enum


class QueryReturnType(Enum):
    NONE = 0
    ROWS_SELECTED = 1
    LAST_INSERT_ID = 2
    ROW_CHANGE_COUNT = 3


class DBException(Exception):
    '''
    Nofus for database exception
    '''
    def __init__(self, message: str, code: int = 0, previous: Optional[Exception] = None):
        super().__init__(message)
        self.code = code
        self.previous = previous

    def __str__(self) -> str:
        return f"{self.__class__.__name__}: {self.args[0]}"


class DBConnect:
    '''
    A wrapper class for MariaDB connections.
    Provides:
        Seamless failover between multiple servers.
        Easy utility functions for identifying table columns and enum values.
        Emulates prepared statements into dumps of constructed queries for debugging.
        Tracks query count and last query run.
        Auto-rollback of transactions when a query fails.
        Pass an array as a value to a query; provides auto-expansion of array to comma-delimited values.
        Provides a safe mechanism to validate table and column names.
    '''

    def __init__(self, conn: Optional[dict|list] = None, debug: bool = False):
        '''
        Requires valid MariaDB connection authentication info

        Args:
            conn: A dict, or list of dicts, containing connection information
            debug: Flag to enable debug mode
        '''
        self._servers: List[Dict[str, Any]] = []
        self._server_index: Optional[int] = None
        self._query_count: int = 0
        self._last_query: Optional[str] = None
        self._transaction: bool = False
        self._connection: Optional[mariadb.Connection] = None
        self._cursor: Optional[mariadb.Cursor] = None
        self._debug: bool = debug
        self._auto_dump: bool = False
        self._err_message: Optional[str] = None
        self._exceptions: bool = True
        self._stderr: bool = True

        if conn:
            self.set_connection_info(conn)

    def set_connection_info(self, conn: Optional[dict|list]) -> bool:
        '''
        Set connection information to the database.

        Args:
            conn: A dict containing connection information, or
                  a list of dicts for multiple servers to attempt to connect to.

        Returns:
            bool: True if connection info validated

        Example conn with multiple servers defined:
            conn = [
              {
                'host'=>'primarymysql.example.com',
                'username'=>'my_user',
                'password'=>'my_pw',
                'database'=>'my_db',
                'port'=>3306            # optional, defaults to 3306
              },
              {
                'host'=>'secondarymysql.example.com',
                'username'=>'my_user',
                'password'=>'my_pw',
                'database'=>'my_db'
              }
            ]
        '''
        # Handle single server case
        if isinstance(conn, dict) and 'host' in conn:
            conn = [conn]

        # Validate connection info
        if isinstance(conn, list):
            for server in conn:
                server_info = {'port': 3306}
                for attr in ['host', 'username', 'password', 'database']:
                    if attr in server and server[attr] and str(server[attr]).strip():
                        server_info[attr] = server[attr]

                # Handle optional port
                if 'port' in server:
                    try:
                        server_info['port'] = int(server['port'])
                    except ValueError:
                        continue

                # Ensure all required fields exist
                if len(server_info) == 5:
                    self._servers.append(server_info)

        if not self._servers:
            self._trigger_error("No valid DB server authentication provided.")
            return False
        return True

    def set_debug_mode(self, enabled: bool = True, dump_output: bool = True) -> None:
        '''
        Set debug mode and auto dump settings.

        Args:
            enabled: Enable/disable debug mode
            dump_output: Enable/disable auto dumping debug info
        '''
        self._debug = enabled
        self._auto_dump = dump_output

    def handle_errors_with(self, exceptions: bool = True, stderr: bool = True) -> None:
        '''
        Set how errors should be handled.

        Args:
            exceptions: Throw exceptions if True
            stderr: Write errors to stderr if True
        '''
        self._exceptions = exceptions
        self._stderr = stderr

    def connection_exists(self) -> bool:
        '''Check if a connection to the database exists.'''
        return self._connection is not None

    def escape_identifier(self, name: str, backticks: bool = True) -> str:
        '''
        Escape identifiers for use in a query.

        Args:
            name: The potentially dangerous identifier
            backticks: Whether to surround with backticks

        Returns:
            str: The safe identifier, or empty string if invalid
        '''
        # Get all valid table and column names
        valid_identifiers = self.get_tables() + self.get_all_columns()

        for valid in valid_identifiers:
            if name == valid:
                safe = valid
                if backticks:
                    safe = f"`{safe.replace('`', '``')}`"
                return safe
        return ""

    def get_connection(self) -> Optional[mariadb.Connection]:
        '''
        Get the current connection object.
        '''
        return self._connection

    def create(self, reinitialize: bool = False) -> bool:
        '''
        Create a connection to a MariaDB server.

        Args:
            reinitialize: If True, close existing connection first

        Returns:
            bool: True if connection exists or was created
        '''
        if reinitialize:
            self.close()

        if not self.connection_exists():
            self._transaction = False
            conn_exc = None
            for i, server in enumerate(self._servers):
                try:
                    conn = mariadb.connect(
                        host=server['host'],
                        port=server['port'],
                        user=server['username'],
                        password=server['password'],
                        database=server['database'],
                        autocommit=True
                        # binary=True  # TODO enable with mariadb v2.x
                    )
                    self._server_index = i
                    self._connection = conn
                    self._cursor = None
                    return True
                except Exception as exc:
                    conn_exc = exc
                    continue

            return self._trigger_error("Unable to connect to database.", conn_exc)

        return True

    def close(self) -> None:
        '''
        Close the database connection.
        '''
        try:
            if self._cursor:
                self._cursor.close()
            if self._connection:
                self._connection.close()
        except Exception:
            pass
        self._cursor = None
        self._connection = None

    def get_host(self) -> str:
        '''
        Get the hostname of the connected server.
        '''
        if self._server_index is None:
            return ""
        return self._servers[self._server_index]['host']

    def get_database_name(self) -> str:
        '''
        Get the name of the current database.
        '''
        if not self.create():
            return ""
        return self._servers[self._server_index]['database']

    def quote_fake(self, value: Any) -> Any:
        '''
        Emulate safe-quoting variables (actual query uses prepared statements).

        Args:
            value: Value to escape

        Returns:
            The escaped value or None if connection failed
        '''
        if not self.create():
            return None

        if value is None:
            return 'NULL'

        if not isinstance(value, (int, float)):
            value = self._connection.escape_string(str(value))

        return value

    def _statement_return(self, cursor: mariadb.Cursor) -> str:
        '''
        Get a string representing the query and values for a given SQL statement.

        Args:
            cursor: The cursor object

        Returns:
            str: The dump of query and params
        '''
        return f"FullSQL:\n{cursor.statement}\n"

    def expand_value_location(self, query: str, nth: int, count: int) -> str:
        '''
        Replace a '?' with comma delimited '?'s at the nth occurrence.

        Args:
            query: The query string
            nth: The nth occurrence of '?' to replace
            count: Number of comma delimited '?' to insert

        Returns:
            str: The modified query string
        '''
        if nth <= 0 or count <= 1:
            return query

        replace_str = ",".join(["?"] * count)
        match_count = 0
        query_len = len(query)

        for i in range(query_len):
            if query[i] == '?':
                match_count += 1
            if match_count == nth:
                new_query = query[:i] + replace_str + query[i+1:]
                return new_query
        return query

    def expand_query_placeholders(self, query: str, values: List[Any]) -> Tuple[str, List[Any]]:
        '''
        Replace all anonymous placeholders with arrays with multiple placeholders.

        Args:
            query: The query string
            values: List of values

        Returns:
            Tuple of (modified query, expanded values)
        '''
        expanded_values = []
        placeholder_loc = 0
        for loc, value in enumerate(values):
            if isinstance(value, list):
                if not value:
                    self._trigger_error(
                        "Cannot pass empty list to value placeholder "
                        f"#{placeholder_loc} in query: {query}"
                    )
                    return query, values

                query = self.expand_value_location(query, placeholder_loc + 1, len(value))
                placeholder_loc += len(value) - 1
                expanded_values.extend(value)
            else:
                expanded_values.append(value)
                placeholder_loc += 1

        return query, expanded_values

    def _record_query(self, cursor: mariadb.Cursor) -> None:
        '''
        Record the last query statement attempted.
        '''
        if not self._debug:
            return

        exceed_msg = "LAST QUERY LOG DISABLED : Exceeded 64 MB limit."
        if self._last_query and (self._last_query == exceed_msg or len(self._last_query) > 67108864):
            self._last_query = exceed_msg
        else:
            query_info = self._statement_return(cursor)
            if self._transaction:
                self._last_query += f"\n\n{query_info}"
            else:
                self._last_query = query_info

    def query(self,
        query: Union[str, Tuple[str, mariadb.Cursor, QueryReturnType]],
        values: List[Any] = None,
        dictionary: bool = True,
        fetch_all: bool = True,
        fetch_column: Optional[int] = None,
        record_query: bool = True
    ) -> Union[List[Dict[str, Any]], List[Any], int, None]:
        '''
        Perform a query.

        Args:
            query: Query string or prepared statement tuple
            values: Values to bind to the query
            dictionary: Return rows as dictionaries if True
            fetch_all: If True, fetch all rows; if False, use query_next()
            fetch_column: Fetch values from given column as a list

        Returns:
            List of rows, insert ID, or row count depending on query type.
            If fetch_column is set, instead returns a list of all values for that column.
        '''
        self._query_count += 1

        if values is None:
            values = []

        if not isinstance(values, list):
            values = [values]

        rows = []
        self._err_message = None

        # Close previous cursor if it exists
        if self._cursor is not None:
            self._cursor.close()
        self._cursor = None

        if isinstance(query, str):
            query, values = self.expand_query_placeholders(query, values)
            query = self.prepare(query, fetch_all, dictionary)

        if isinstance(query, tuple) and len(query) == 3 and isinstance(query[1], mariadb.Cursor):
            query, self._cursor, query_type = query
        else:
            return self._trigger_error(
                "Method query() does not have a valid cursor to execute with query."
            )

        try:
            self._cursor.execute(query, values)

            if fetch_all:
                if query_type == QueryReturnType.ROWS_SELECTED:
                    if fetch_column is not None:
                        rows = [row[0] for row in self._cursor.fetchall()]
                    else:
                        rows = self._cursor.fetchall()

        except Exception as exc:
            self.transaction_rollback()
            self._record_query(self._cursor)
            return self._trigger_error_dump("Error: Query execute failed.", exc)

        if fetch_all:
            self._record_query(self._cursor)

        if query_type == QueryReturnType.LAST_INSERT_ID:
            insert_id = self._cursor.lastrowid
            if insert_id and int(insert_id) > 0:
                return int(insert_id)
            return None

        if query_type == QueryReturnType.ROW_CHANGE_COUNT:
            row_count = self._cursor.rowcount
            if isinstance(row_count, int) and row_count >= 0:
                return row_count
            return None

        if fetch_all or query_type in [QueryReturnType.LAST_INSERT_ID, QueryReturnType.ROW_CHANGE_COUNT]:
            self._cursor.close()

        return rows

    def prepare(
        self,
        query: str,
        fetch_all: bool = True,
        dictionary: bool = True,
        reconnect_attempts: int = 1
    ) -> Tuple[mariadb.Cursor, QueryReturnType]:
        '''
        Create cursor; does not actually create a prepared statement. Python library does not
        support client side prepared statements.

        Args:
            query: The query string
            fetch_all: Set the cursor to buffer all rows into memory at query execution time
            reconnect_attempts: Number of reconnect attempts if connection is lost

        Returns:
            Tuple of (query:str, Cursor, QueryReturnType), or None on connection failure
        '''
        self._err_message = None

        # Determine query type
        ret_rows = bool(re.match(r'^\s*(SELECT|SHOW)', query, re.IGNORECASE))
        ret_insertid = bool(re.match(r'^\s*INSERT', query, re.IGNORECASE))
        ret_rowcount = bool(re.match(r'^\s*(UPDATE|REPLACE|DELETE)', query, re.IGNORECASE))
        if re.match(r'^\s*INSERT.*SELECT', query, re.IGNORECASE):
            ret_rows = False
            insert_id = False
            ret_rowcount = True

        query_type = QueryReturnType.NONE
        if ret_rows:
            query_type = QueryReturnType.ROWS_SELECTED
        if ret_insertid:
            query_type = QueryReturnType.LAST_INSERT_ID
        elif ret_rowcount:
            query_type = QueryReturnType.ROW_CHANGE_COUNT

        if not self.create():
            return None

        try:
            cursor = self._connection.cursor(buffered=fetch_all, dictionary=dictionary)
        except Exception as exc:
            if "has gone away" in str(exc):
                if reconnect_attempts > 0:
                    self.close()
                    return self.prepare(query, fetch_all, dictionary, reconnect_attempts - 1)
                return self._trigger_error(
                    "Lost connection to SQL server and could not re-connect.",
                    exc
                )
            return self._trigger_error_dump(
                "SQL could not prepare query; it is not valid or references something"
                f"non-existent.\n{query}",
                exc
            )

        return (query, cursor, query_type)

    def query_loop(self, query: str, values: List[Any] = None, dictionary: bool = True) -> None:
        '''
        Execute a SELECT query for use with query_next().

        Args:
            query: The query string
            values: Values to bind to the query
            dictionary: Return row as dictionary if True
        '''
        if values is None:
            values = []
        self.query(query, values, dictionary=dictionary, fetch_all=False)

    def query_next(self) -> Optional[Union[Dict[str, Any], Any]]:
        '''
        Get the next row from a query.

        Returns:
            Next row or None if no more rows
        '''
        if self._cursor is None:
            return None
        return self._cursor.fetchone()

    def query_row(self,
        query: str,
        values: List[Any] = None,
        dictionary: bool = True
    ) -> Optional[Union[Dict[str, Any], Any]]:
        '''
        Get the first row from a query.

        Args:
            query: The query string
            values: Values to bind to the query
            dictionary: Return row as dictionary if True

        Returns:
            First row or None if no rows
        '''
        if values is None:
            values = []
        rows = self.query(query, values, dictionary=dictionary, fetch_all=True)
        if rows and len(rows) > 0:
            return rows[0]
        return None

    def query_column(self, query: str, values: List[Any] = None, fetch_column: int = 0) -> List[Any]:
        '''
        Get all values from a column.

        Args:
            query: The query string
            values: Values to bind to the query
            fetch_column: Column index to retrieve

        Returns:
            List of column values
        '''
        if values is None:
            values = []
        return self.query(query, values, dictionary=False, fetch_column=fetch_column)

    def query_return(self, query: str, values: List[Any] = None, supress_warning = False) -> str:
        '''
        Return an emulated query with values escaped.

        Args:
            query: The query string
            values: Values to bind to the query

        Returns:
            str: The emulated query string
        '''
        if values is None:
            values = []

        if not supress_warning:
            result = "\n-- [WARNING] This only EMULATES what the prepared statement will run.\n\n"

        query, values = self.expand_query_placeholders(query, values)

        for i, value in enumerate(values):
            values[i] = self.quote_fake(value)

        query = query.replace("%", "%%")  # Escape existing % chars
        query = query.replace("?", "%s")

        result += query % tuple(values) + "\n\n"
        return result

    def enum_values(self, table: str, column: str) -> List[str]:
        '''
        Get all possible enum values from a column.

        Args:
            table: Table name
            column: Column name

        Returns:
            List of enum values in index order
        '''
        enums = []
        safe_table = self.escape_identifier(table)
        safe_column = self.escape_identifier(column, backticks=False)
        query = f"SHOW COLUMNS FROM {safe_table} LIKE '{safe_column}'"

        rows = self.query(query, dictionary=False)
        if rows and len(rows) > 0:
            column_info = rows[0]
            matches = re.findall(r"'([^']*)'", column_info[1])
            if matches:
                enums = [match for match in matches]

        return enums

    @cache
    def get_tables(self) -> List[str]:
        '''
        Get a list of all table names for the current database.
        '''
        rows = self.query("SHOW TABLES", dictionary=False, record_query=False)
        return list({row[0] for row in rows})

    @cache
    def get_all_columns(self) -> List[str]:
        '''
        Get a list of all column names for all tables in the database.
        '''
        table_infos = self.get_table_columns()
        return list({info['name'] for info in table_infos})

    def get_table_columns(self, table_name: Optional[str] = None) -> List[Dict[str, Any]]:
        '''
        Get column information for a table.

        Args:
            table_name: Table name (None for all tables)

        Returns:
            List of column information dictionaries
        '''
        query = '''
            SELECT column_name, column_default, is_nullable, data_type,
                   character_maximum_length, numeric_precision, column_type,
                   column_key, extra
            FROM information_schema.columns
            WHERE table_schema = ?
            '''
        values = [self.get_database_name()]

        if table_name is not None:
            query += " AND table_name = ?"
            values.append(table_name)

        query += " ORDER BY ordinal_position ASC"

        rows = self.query(query, values, dictionary=True, record_query=False)

        columns = []
        for row in rows:
            columns.append({
                'name': row['column_name'],
                'is_nullable': row['is_nullable'] != 'NO',
                'is_autokey': 'auto_increment' in row['extra'].lower()
            })

        return columns

    def transaction_start(self, read_committed: Optional[bool] = None) -> Optional[bool]:
        '''
        Start a transaction.

        Args:
            read_committed: Set transaction isolation level. If True, isolation to "READ COMMITTED";
                            If False, sets it to "REPEATABLE READ"; if left None, no transaction
                            level is set (MariaDB default is "REPEATABLE READ").

        Returns:
            bool: True if transaction started, False if already in transaction, None if error
        '''
        self._err_message = None
        if not self.create():
            return None

        if not self._transaction:
            if read_committed is True:
                self.query(
                    "SET TRANSACTION ISOLATION LEVEL READ COMMITTED", record_query=False
                )
            elif read_committed is False:
                self.query(
                    "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ", record_query=False
                )

            self._connection.begin()
            self._transaction = True
            self._last_query = ""
            return True

        return False

    def transaction_commit(self) -> None:
        '''
        Commit the current transaction.
        '''
        if self._transaction:
            self._connection.commit()
            self._transaction = False

    def transaction_rollback(self) -> bool:
        '''
        Rollback the current transaction.

        Returns:
            bool: True if rolled back, False if no transaction
        '''
        if self._transaction:
            self._connection.rollback()
            self._transaction = False
            return True
        return False

    def is_transaction_started(self) -> bool:
        '''
        Check if a transaction is currently active.
        '''
        return self._transaction

    def get_query_count(self) -> int:
        '''
        Get the number of queries executed.
        '''
        return self._query_count

    def get_last_query(self) -> Optional[str]:
        '''
        Get the last query executed. Debug mode only.
        '''
        return self._last_query

    def _trigger_error(
        self,
        message: str,
        exc: Optional[Exception] = None,
        dump: bool = False
    ) -> bool:
        '''
        Handle errors.

        Args:
            message: Error message
            exc: Exception that caused the error
            dump: Whether to dump debug info

        Returns:
            bool: False to indicate error
        '''
        self._err_message = message
        if self._stderr:
            print(message, exc, file=sys.stderr)

        if self._exceptions:
            if self._debug :
                # Trigger dump if enabled
                self.get_error_info(dump, exc=exc)
                raise DBException(message) from exc
            else:
                raise DBException("A database error has occurred.", code=0, previous=exc)

        return False

    def _trigger_error_dump(self, message: str, exc: Optional[Exception] = None) -> bool:
        '''
        Trigger error with dump of query information if enabled.
        '''
        return self._trigger_error(message, exc, True)

    def get_error_info(self, dump: bool = False, exc: Exception = None) -> str:
        '''
        Get information about the last error.

        Args:
            dump: Whether to dump to output

        Returns:
            str: Error information
        '''
        output = StringIO()
        output.write("=======================================================\n")
        output.write("** DBConnect Error **\n")
        output.write(f"{self._err_message}\n")

        if dump:
            if self._cursor is not None:
                output.write("=======================================================\n")
                output.write("** SQL Error Info **\n")
                output.write(f"Exception {exc}\n\n")
                output.write(self._statement_return(self._cursor) + "\n\n")

            if self._last_query:
                output.write("=======================================================\n")
                output.write("** Query Log **\n")
                output.write(f"{self._last_query}\n\n")

        output.write("=======================================================\n")
        error_info = output.getvalue()

        if self._auto_dump and dump:
            print(f"<pre>{html.escape(error_info)}</pre>")

        return error_info
