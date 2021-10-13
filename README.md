![](./docs/images/logo.png)

An easy to use rpc framework for enabling fast inter-process, inter-container, or inter-host communication

Easily share functions between hosts, processes, containers without the complexity of defining non-native python types or proxy modules.

[![Documentation Status](https://readthedocs.org/projects/easyrpc/badge/?version=latest)](https://easyrpc.readthedocs.io/en/latest/?badge=latest) [![PyPI version](https://badge.fury.io/py/easyrpc.svg)](https://pypi.org/project/easyrpc/)

## Documentation
[easyrpc.readthedocs.io](https://easyrpc.readthedocs.io)

## Key Features
- No predefined proxy functions at the remote endpoints
- Easily group and share functons among hosts / processes using Namespaces / Namespace Groups
- Proxy functions parameters are validated as if defined locally.
- Optional: pre-flight encyrption 
- No strict RPC message structure / size limit, within json serializable constraints

## Quick Start

```bash
$ virtualenv -p python3.7 easy-rpc-env

$ source easy-rpc-env/bin/activate

(easy-rpc-env)$ pip install easyrpc
```

## Basic Usage:

```python
# server.py
from fastapi import FastAPI
from easyrpc.server import EasyRpcServer

server = FastAPI()

ws_server_a = EasyRpcServer(server, '/ws/server_a', server_secret='abcd1234')

@ws_server_a.origin(namespace='public')
def good_func_a(a, b, c):
    print(f"good_func_a {a} {b} {c}")
    return {"good_func_a": [a, b, c]}
```
```python
# client.py
import asyncio
from easyrpc.proxy import EasyRpcProxy

async def main():
    proxy = await EasyRpcProxy.create(
        '0.0.0.0', 
        8090, 
        '/ws/server_a', 
        server_secret='abcd1234',
        'namespace='public'
    )

    good_func_a = proxy['good_func_a']
    result = await good_func_a(1, 5, 7)
    print(result)

asyncio.run(main())
```

## Recipes
See other usage examples in [Recipes](https://github.com/codemation/easyrpc/tree/main/recipes)
- [basic](https://github.com/codemation/easyrpc/tree/main/recipes/basic)
- [clusters](https://github.com/codemation/easyrpc/tree/main/recipes/clusters)
- [FastAPI-Shared-Database](https://github.com/codemation/easyrpc/tree/main/recipes/fastapi/shared_database)
- [Generators](https://github.com/codemation/easyrpc/tree/main/recipes/generators)


## Supported Functions Features
- async def & def
- async generators & generators
- *args, **kwargs
- positional & default parmeters
- TODO - type annotations

## Common Use Cases
- State sharing among forked workers 
- Shared Database connections / cache 
- Shared Queues
- Worker Pooling - Easy centralization for workers and distribution of work.  
- Function Chaining
