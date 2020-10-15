# easyrpc
An easy to use rpc framework for enabling fast inter-process, inter-host communication

Easily share functions between hosts, processes, containers without the complexity of defining non-native python types or proxy modules.

## Key Features
- No need to predefine proxy functions at the remote endpoints
- Proxy functions parameters are validated as if defined locally.
- Optional pre-flight encyrption 
- The use of websockets means a single TCP stream can be used or all functions, which means less time waiting for TCP to get to know each other via 3-way-handshake(i.e 2 RTTs).
- Data can be transported via any JSON serializable data-types, with no limit on message size or nested depth.

## Quick Start

    $ virtualenv -p python3.7 easy-rpc-env

    $ source easy-rpc-env/bin/activate

    (easy-rpc-env)$ pip install easyrpc

## Basic Usage:

 

    # server.py
    from fastapi import FastAPI
    from easyrpc.server import EasyRpcServer

    server = FastAPI()

    ws_server_a = EasyRpcServer(server, '/ws/server_a', server_secret='abcd1234')

    @ws_server_a.origin
    def good_func_a(a, b, c):
        print(f"good_func_a {a} {b} {c}")
        return {"good_func_a": [a, b, c]}

<br> 

    # client.py
    import asyncio
    from easyrpc.proxy import EasyRpcProxy

    async def main():
        p = await EasyRpcProxy.create('0.0.0.0', 8090, '/ws/server_a', server_secret='abcd1234')

        good_func_a = p.proxy_funcs['good_func_a']
        result = await good_func_a(1, 5, 7)
        print(result)

    asyncio.run(main())



## Advanced Usage

    # server.py
    from fastapi import FastAPI
    from easyrpc.server import EasyRpcServer

    server = FastAPI()

    ws_server_a = EasyRpcServer(server, '/ws/server_a', server_secret='abcd1234')

    ws_server_b = EasyRpcServer(server, '/ws/server_b', server_secret='abcd1234')

    @ws_server_a.origin
    def good_func_a(a, b, c):
        print(f"good_func_a {a} {b} {c}")
        return {"good_func_a": [a, b, c]}

    @ws_server_b.origin
    def good_func_b(a, b, c):
        print(f"good_func_b {a} {b} {c}")
        return {"good_func_b": [a, b, c]}

    # Register to both EasyRpcServer servers
    # availabe for both /ws/server_a & /ws/server_b proxies

    @ws_server_a.origin
    @ws_server_b.origin
    def good_func_c(a, **kw):
        print(f"good_func_c {a} {kw}")
        return {"good_func_c": [a, kw]}

<br>

    # client.py
    import asyncio
    from easyrpc.proxy import EasyRpcProxy

    async def main():
        p = await EasyRpcProxy.create('0.0.0.0', 8090, '/ws/server_a', server_secret='abcd1234')

        good_func_a = p.proxy_funcs['good_func_a']
        result = await good_func_a(1, 5, 7)
        print(result)
        
        result = await p.proxy_funcs['good_func_c'](1, keyword='value')
        print(result)

        print(p.proxy_funcs)

    asyncio.run(main())

Output:

    # Start server
    (easy-rpc-env)$ uvicorn --host 0.0.0.0 --port 8090 test_server:server
    10-14 23:18 wsRpc-server /ws/server_a WARNING  ORIGIN - registered function get_registered_functions 
    10-14 23:18 wsRpc-server /ws/server_b WARNING  ORIGIN - registered function get_registered_functions 
    10-14 23:18 wsRpc-server /ws/server_a WARNING  ORIGIN - registered function good_func_a 
    10-14 23:18 wsRpc-server /ws/server_b WARNING  ORIGIN - registered function good_func_b 
    10-14 23:18 wsRpc-server /ws/server_b WARNING  ORIGIN - registered function good_func_c 
    10-14 23:18 wsRpc-server /ws/server_a WARNING  ORIGIN - registered function good_func_c 
    INFO:     ('127.0.0.1', 57406) - "WebSocket /ws/server_a" [accepted]
    10-14 23:36 uvicorn.error INFO     ('127.0.0.1', 57406) - "WebSocket /ws/server_a" [accepted]
    10-14 23:36 wsRpc-server /ws/server_a WARNING  created websocket connection with endpoint 44d87c38-0e65-11eb-8ae3-2f2bf6388831
    good_func_a 1 5 7
    good_func_c 1 {'keyword': 'value'}
    10-14 23:36 wsRpc-server /ws/server_a WARNING  deleted websocket connection with endpoint 44d87c38-0e65-11eb-8ae3-2f2bf6388831

<br>

    # Client
    $ python test_client.py 
    {'good_func_a': [1, 5, 7]}
    {'good_func_c': [1, {'keyword': 'value'}]}
    {'get_registered_functions': <function create_proxy_from_config.<locals>.__proxy__ at 0x7f4e8d238200>, 'good_func_a': <function create_proxy_from_config.<locals>.__proxy__ at 0x7f4e8d24dcb0>, 'good_func_c': <function create_proxy_from_config.<locals>.__proxy__ at 0x7f4e8d24df80>}


A Helpful look at proxy signature

    # Client
    good_func_c = p.proxy_funcs['good_func_c']
    help(good_func_c)

    Help on function good_func_c_proxy in module easyrpc.register:

    good_func_c_proxy(a, **kw)


## Under the hood 
easyrpc is made easy via the amazing [fastapi](https://github.com/tiangolo/fastapi) framework for handling server side websocket communciation, [aiohttp](https://github.com/aio-libs/aiohttp) for the client-side websocket communication,  [makefun](https://github.com/smarie/python-makefun) along with some standard library 'inspect' magic  for translating origin functions into remote-useable functions with parameter validation, and lastly [pyjwt](https://github.com/jpadilla/pyjwt) for authentication & encryption.

Registered functions are made available as callables which return co-routines and thus 'awaitable' to the remote-endpoints, this is true for both async and non-async registered functions. Due to this, the functions must be awaited within a running event_loop. When called, the input parameters are verified via the origin functions signature. 

## Supported Functions Features
- async def & def
- *args, **kwargs
- positional & default parmeters
- TODO - type annotations

## Common Use Cases
- Long running processes where inter-process, intracluster communication occurs frequently. 
- Function Namespaces
- Function Chaining 
- TODO - TBD