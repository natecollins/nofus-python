# NOFUS: Nate's One-File Utilities Stash

## About NOFUS

A collection of single purpose classes for common tasks, focusing on simple and
straightforward use. Each class can be taken and used individually and requires
no external dependencies.  

## Uses

* [ConfigFile: No Hassle Config File Parser](#configfile-no-hassle-config-file-parser)
* [Logger: Simplified Alternate Logging Interface](#logger-simplified-alternate-logging-interface)
* [DBConnect: Quick interface for making MariaDB queries](#dbconnect-quick-interface-for-making-mariadb-queries)

### ConfigFile: No Hassle Config File Parser

Example Config:  
```
[email]
admin    = admin@example.com
reply_to = feedback@example.com

[auth.sql]
host = sql.example.com
db   = mydbname
user = sqluser
pw   = "secret_passwd"

[auth.ldap]
uri = "ldap://ldap1.example.com:389"
uri = "ldap://ldap2.example.com:389"
uri = "ldap://ldap3.example.com:389"
```

Example Use:  
```
from nofus import ConfigFile

conf = ConfigFile("/path/to/my.conf")
if not conf.load():
    print(conf.errors())
else:
    admin_email = conf.get("email.admin")
    reply_email = conf.get("email.reply_to", default="donotreply@example.com")

    sqlauth     = conf.get("auth.sql")
    sql_host    = sqlauth.get("host")
    sql_db      = sqlauth.get("db")
    sql_user    = sqlauth.get("user")
    sql_pw      = sqlauth.get("pw")

    ldap_uris   = conf.get_list("auth.ldap.uri")
```

### Logger: Simplified Alternate Logging Interface

Example Use:  
```
from nofus import Logger

# Fast setup, default to logging LOG_DEBUG and higher
Logger.initialize('/tmp/myfile.log')
Logger.info("Info!")
Logger.notice("Notice!")
Logger.warning("Warning!")
Logger.error("Error!")
Logger.critical("Critical!")

# Easily put an exception stack trace into the log
try:
    1/0
except ZeroDivisionError as exc:
    Logger.info("Caught something.", exc_info=exc)

# Disable logging
Logger.disable()

# Set custom log level
Logger.initialize('/tmp/myfile.log', Logger.LOG_TRACE)
Logger.trace("Trace!")

# Check log level
if Logger.is_enabled(Logger.LOG_DEBUG):
    Logger.debug("Yep, we're debugging.")

# Or Define a custom logger
from nofus import LoggingInterface
class CustomLogger(LoggingInterface):
    def __init__(self, log_file=None, log_level=None):
        if log_level is None:
            log_level = Logger.LOG_LOW
        # Customize your init

    def make_log(self, entry, log_level):
        # Customize your log actions

Logger.register(CustomLogger())
```

### DBConnect: Quick interface for making MariaDB queries

Example Use:  
```
from nofus import DBConnect

conn = [
    {"host": "127.0.0.1", "port": 3306, "database": "myapp", "username": "appuser", "password": "secret"}
]

db = DBConnect(conn)

# Simple query, rows being a list of dict with keys being table column names
rows = db.query("SELECT * FROM users WHERE username = ?", ["soandso"])

# Simple query, getting just first row. Returns None if no rows found
row = db.query_row("SELECT * FROM users WHERE username = ?", ["soandso"])

# Get a column of values as a list
list_user_ids = db.query_column("SELECT id FROM users")

# Print what a query might look like with values inserted, but doesn't run query
query_string = db.query_return("SELECT * FROM users WHERE username = ?", ["soandso"])

# For large queries, retrieve rows one at a time instead of all at once
db.query_loop("SELECT * FROM very_large_table")
while row := db.query_next():
    print(row)

# Safe handling of table and column names; returns empty string if invalid
safe_table_name = db.escape_identifer(table_name)
safe_column_name = db.escape_identifer(column_name)
if safe_table_name and safe_column_name:
    db.query(f"SELECT {safe_column_name} FROM {safe_table_name}")

# Return last insert id for single record inserts
new_user_id = db.query("INSERT INTO users SET username = ?", ['soando'])

# Returns row count for update, insert, delete, and multi-insert queries
rows_changed = db.query("UPDATE users SET last_updated = NOW()")

# Transactions
db.transaction_start()  # Default REPEATABLE READ, pass True for READ COMMITTED.
db.is_transaction_started()
db.transaction_commit()
db.transaction_rollback()
```

## Installation

If all you need is one class, you can just grab a file and throw it in your project.  

Or you can install the whole stack using `pip`:  
```
pip install nofus
```

## License

NOFUS is covered by the Simplified BSD License.  
