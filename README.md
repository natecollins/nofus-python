# NOFUS: Nate's One-File Utilities Stash
## About NOFUS
A collection of single purpose classes for common tasks, focusing on simple and
straightforward use. Each class can be taken and used individually and requires
no external dependencies.  

## Uses

### ConfigFile : No Hassle Config File Parser
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

## Installation
If all you need is one class, you can just grab a file and throw it in your project.  

Or you can install the whole stack using `pip`:  
```
TODO
```

## License
NOFUS is covered by the Simplified BSD License.  

