## Shared Database conection
Database connections, table model logic & querries can be shared via easyrpc framework

!!! Danger "Before easyrpc"
    - Apps that needs to access and/or store data in a database needs a separate connection, table definitions / models configured
    - Caching would require a separate application layer component such as redis / memcached, and extra invalidation logic. 

!!! TIP "With easyrpc"
    - Multiple Apps can access and use a single database connection 
    - Shared database connection allows for caching requests since cache can be created / updated / invalidated from a single process.

### Examples  
- [FastAPI-Shared-Database](https://github.com/codemation/easyrpc/tree/main/recipes/fastapi/shared_database)

### Templates
- [aiopyql-rest-endpoint](https://github.com/codemation/aiopyql-rpc-endpoint) - Quickly start a sqlite / mysql / postgres connected aiopyql easyrpc endpoint, which can be connected using an EasyRpcProxyDatabase()

### EasyRpcProxyDatabase
!!! TIP
    EasyRpcProxyDatabase provides remote functionality to an [aiopyql](https://github.com/codemation/aiopyql) connected database, to create tables, access, update, delete, and query data.    
    
    All applications connected via the EasyRpcProxyDatabase() namespace, have access to new & existing tables, query cache.


Shared aiopyql database & EasyRpcProxyDatabase

```bash
# Start an aiopyql-rest-endpoint instance

$ mkdir dbtest

$ docker run -d --name aiopyql-testdb \
    -p 8190:8190 \
    -e DB_TYPE='sqlite' \
    -e DB_NAME='testdb' \
    -e RPC_SECRET='abcd1234' \
    -v dbtest:/mnt/pyql-db-endpoint \
    joshjamison/aiopyql-rpc-endpoint:latest
```

```python
# client.py

import asyncio
from easyrpc.tools.database import EasyRpcProxyDatabase

async def main():

    db = await EasyRpcProxyDatabase.create(
        'localhost', 
        8190, 
        '/ws/testdb', 
        server_secret='abcd1234',
        namespace='testdb'
    )

    create_table_result = await db.create_table(
        'keystore',
        [
            ['key', 'str', 'UNIQUE NOT NULL'],
            ['value', 'str']
        ],
        prim_key='key',
        cache_enabled=True
    )
    print(f"create_table_result: {create_table_result}")

    show_tables = await db.show_tables()

    print(f"show tables: {show_tables}")

    query = 'select * from sqlite_master'
    run_query = await db.run(query)

    print(f"run_query results: {run_query}")

    keystore = db.tables['keystore']

    # insert
    await keystore.insert(
        **{'key': 'new_key', 'value': 'new_value'}
    )

    # update
    await keystore.update(
        value='updated_value',
        where={'key': 'new_key'}
    )

    # delete
    await keystore.delete( 
        where={'key': 'new_key'}
    )

    # select
    selection = await keystore.select( 
        '*',
        where={'key': 'new_key'}
    )
    print(f"selection: {selection}")

asyncio.run(main())
```