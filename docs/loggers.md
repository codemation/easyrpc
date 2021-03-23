## Loggers
easyrpc can be used to share existing python standard library logger with proxy or server proxys and centralize logging to one location
<br>

!!! NOTE  "Poxies created as EasyRpcProxyLogger inhert the standard library logging methods"
    * info
    * warning
    * error
    * debug
    * exception - including full stack traces

!!! TIP 
    As with all proxied functions, each should be awaited

#### Logging Server
```python
# server_a.py
import logging
from fastapi import FastAPI
from easyrpc.server import EasyRpcServer

logging.basicConfig()

server = FastAPI()

@server.on_event('startup')
async def setup():

    logger = logging.getLogger()

    rpc_server = EasyRpcServer(server, '/ws/server', server_secret='abcd1234', debug=True)

    rpc_server.register_logger(logger, namespace='logger')
```

#### Logging Client
```python
# share logging with a basic client
import aysncio
from easyrpc.tools.logger import EasyRpcProxyLogger

async def main():

    logger = await EasyRpcProxyLogger.create(
        '0.0.0.0', 
        8220, 
        '/ws/server', 
        server_secret='abcd1234', 
        namespace='logger'
    )
    await logger.warning(f"client - started from {logger.session_id}")

aysncio.run(main())
```
#### EasyRpcServer -> EasyRpcServer Logger
```python
# server_b.py
# share logging with another server
from fastapi import FastAPI
from easyrpc.server import EasyRpcServer

server = FastAPI()

@server.on_event('startup')
async def setup():
    #server
    rpc_server = EasyRpcServer(
        server, 
        '/ws/server', 
        server_secret='efgh1234'
    )

    logger = await rpc_server.create_server_proxy_logger(
        '0.0.0.0', 8220, '/ws/server', server_secret='abcd1234', namespace='logger'
    )

    await logger.error(f"server_b - starting with id {ws_server_b.server_id}")
```