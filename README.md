# NOFUS: Nate's One-File Utilities Stash
## About NOFUS
A collection of single purpose classes for common tasks, focusing on simple and
straightforward use. Each class can be taken and used individually and requires
no external dependencies.  

## Uses
* [ConfigFile: No Hassle Config File Parser](#configfile-no-hassle-config-file-parser)
* [Logger: Simplified Alternate Logging Interface](#logger-simplified-alternate-logging-interface)

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
from logger import Logger

# Fast setup, default to logging LOG_DEBUG and higher
Logger.initialize('/tmp/myfile.log')
Logger.info("Info!")
Logger.notice("Notice!")
Logger.warning("Warning!")
Logger.error("Error!")
Logger.critical("Critical!")

# Disable logging
Logger.disable()

# Set log level
Logger.initialize('/tmp/myfile.log', Logger.LOG_TRACE)
Logger.trace("Trace!")

# Check log level
if Logger.is_enabled(Logger.LOG_DEBUG):
    Logger.debug("Debug!")

# Or Define a custom logger
from logger import LoggingInterface
class CustomLogger(LoggingInterface):
    def __init__(self, log_file=None, log_level=None):
        if log_level is None:
            log_level = Logger.LOG_LOW
        # Customize your init

    def make_log(self, entry, log_level):
        # Customize your log actions

Logger.register(CustomLogger())
```

## Installation
If all you need is one class, you can just grab a file and throw it in your project.  

Or you can install the whole stack using `pip`:  
```
TODO
```

## License
NOFUS is covered by the Simplified BSD License.  

