# EasyRpc

An easy to use rpc framework for enabling fast inter-process, inter-container, or inter-host communication

Easily share functions between hosts, processes, containers without the complexity of defining non-native python types or proxy modules.

## Key Features
- No predefined proxy functions at the remote endpoints
- Easily group and share functons among hosts / processes using Namespaces / Namespace Groups
- Proxy functions parameters are validated as if defined locally.
- Optional: pre-flight encyrption 
- No strict RPC message structure / size limit, within json serializable constraints

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

    @ws_server_a.origin(namespace='public')
    def good_func_a(a, b, c):
        print(f"good_func_a {a} {b} {c}")
        return {"good_func_a": [a, b, c]}

<br> 

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
## Recipies
See other usage examples in [recipies](https://github.com/codemation/easyrpc/tree/main/recipies)
- [basic](https://github.com/codemation/easyrpc/tree/main/recipies/basic)
- [clusters](https://github.com/codemation/easyrpc/tree/main/recipies/clusters)
- [FastAPI-Shared-Database](https://github.com/codemation/easyrpc/tree/main/recipies/fastapi/shared_database)
- [Generators](https://github.com/codemation/easyrpc/tree/main/recipies/generators)

## Usage with multiple namespaces

    # server.py
    from fastapi import FastAPI
    from easyrpc.server import EasyRpcServer

    server = FastAPI()

    easy_server = EasyRpcServer(server, '/ws/easy', server_secret='abcd1234')

    @easy_server.origin(namespace='private')
    def private_function(a, b, c):
        print(f"private_function {a} {b} {c}")
        return {"private_function": [a, b, c]}

    @easy_server.origin(namespace='public')
    def public_func(a, b, c):
        print(f"public_func {a} {b} {c}")
        return {"public_func": [a, b, c]}

    @easy_server.origin(namespace='public')
    @easy_server.origin(namespace='private')
    def open_function(a, **kw):
        print(f"open_function {a} {kw}")
        return {"open_function": [a, kw]}

<br>

    # client.py
    import asyncio
    from easyrpc.proxy import EasyRpcProxy

    async def main():
        easy_proxy = await EasyRpcProxy.create(
            '0.0.0.0', 
            8220, 
            '/ws/easy', 
            server_secret='abcd1234',
            namespace='private'
        )

        result = await easy_proxy['private_function'](1, 5, 7)
        print(result)
        
        result = await easy_proxy.proxy_funcs['open_function'](1, keyword='value')
        print(result)

        print(easy_proxy.proxy_funcs)

    asyncio.run(main())

Output:

    # Start server
    $ uvicorn --host 0.0.0.0 --port 8220 bsc_server:server
    11-06 22:10 EasyRpc-server /ws/easy WARNING  ORIGIN - registered function private_function in private namespace
    11-06 22:10 EasyRpc-server /ws/easy WARNING  ORIGIN - registered function public_func in public namespace
    11-06 22:10 EasyRpc-server /ws/easy WARNING  ORIGIN - registered function open_function in private namespace
    11-06 22:10 EasyRpc-server /ws/easy WARNING  ORIGIN - registered function open_function in public namespace


<br>

    # Client
    $ python bsc_client.py 
    {'private_function': [1, 5, 7]}
    {'open_function': [1, {'keyword': 'value'}]}
    {'private_function': <function create_proxy_from_config.<locals>.__proxy__ at 0x7fa0be5b4dd0>, 'open_function': <function create_proxy_from_config.<locals>.__proxy__ at 0x7fa0bdf3f050>}



A Helpful look at proxy signature

    # Client
    help(easy_proxy['private_function'])

    Help on function open_function in module easyrpc.register:

    open_function(a, **kw)

## Generators
easyrpc can proxy registered generators & async generators with the same constraints as registered functions. i.e input / output should be JSON serializable.

Like registered functions, normal generators are converted into async generators at the proxy and must be iterated over using 'async for' or await generator.asend(None)

<br>

    #server 
    from fastapi import FastAPI
    from easyrpc.server import EasyRpcServer

    server = FastAPI()

    easy_server = EasyRpcServer(server, '/ws/easy', server_secret='abcd1234')

    @easy_server.origin(namespace='private')
    def private_generator(work: dict):
        for item in work:
            yield item

    @easy_server.origin(namespace='public')
    async def public_generator(work: dict):
        for item in work:
            yield item


<br> 

    # client.py
    import asyncio
    from easyrpc.proxy import EasyRpcProxy

    async def main():
        private = await EasyRpcProxy.create(
            '0.0.0.0', 
            8220, 
            '/ws/easy', 
            server_secret='abcd1234',
            namespace='private'
        )

        public = await EasyRpcProxy.create(
            '0.0.0.0', 
            8220, 
            '/ws/easy', 
            server_secret='abcd1234',
            namespace='public'
        )

        # basic generator usage
        async for item in await private['private_generator']([1, 2, 'a', 'b', 3, 4]):
            print(f"async for {item}")
        
        public_generator = await public['public_generator']([1, 2, 'a', 'b', 3, 4])
        while True:
            try:
                result = await public_generator.asend(None)
                print(f"asend result: {result}")
            except StopAsyncIteration:
                break
                
    asyncio.run(main())

## Clustering / EasyRpcServer Chaining / Namespacing 
An EasyRpcServer can register functions in multiple namespaces, if unspecified 'Default' is used. 
<br>

    easy_server = EasyRpcServer(server, '/ws/easy', server_secret='abcd1234')

Registration can be performed using the Decorator or via easy_server.orgin(f, namespace='Namespace')

    # Decorator
    @easy_server.orgin # default
    easy_server.orgin(namespace='Public')

    # Register progamatically
    def foo(x):
        return x
    easy_server.orgin(foo, namespace='private')


### Clustering

EasyRpcServer namepaces can be grouped together with other EasyRpcServer instances, to form "clusters"

#### Cluster Features:
- Dynamically Share new / existing functions amongst cluster members  
- Proxy and Reverse proxy functions automatically propogate changes up / downstream every 15 seconds
- Access to all functions anywhere in a chain

<br>
 
    # Server A - port 8220
    server = FastAPI()
    server_a = EasyRpcServer(server, '/ws/server_a', server_secret='abcd1234')

    @server_a.origin(namespace='public')
    def a_func(a):
        return {'a': a}
<br>

    # Server B - port 8221
    server = FastAPI()
    server_b = EasyRpcServer(server, '/ws/server_b', server_secret='abcd1234')

    @server_b.origin(namespace='public')
    def b_func(b):
        return {'b': b}
    
    @server.on_event('startup)
    async def setup()
        await server_b.create_server_proxy(
            0.0.0.0, 8220, '/ws/server_a', server_secret='abcd1234', namespace='public'
        )
<br>

    # Server C - port 8222
    server = FastAPI()
    server_c = EasyRpcServer(server, '/ws/server_c', server_secret='abcd1234')

    @server_c.origin(namespace='public')
    def c_func(c):
        return {'c': c}
    
    @server.on_event('startup)
    async def setup()
        await server_c.create_server_proxy(
            0.0.0.0, 8221, '/ws/server_b', server_secret='abcd1234', namespace='public'
        )

Servers A, B or C can now be accessed via a Proxy to use a_func, b_func, or c_func:
    
    # client.py
    import asyncio
    from easyrpc.proxy import EasyRpcProxy

    async def main():
        public = await EasyRpcProxy.create(
            '0.0.0.0', 
            8221, 
            '/ws/server_b', 
            server_secret='abcd1234',
            namespace='public'
        )
    
        await public['a_func']('a')
        await public['b_func']('b')
        await public['c_func']('c')



#### Constraints:
- An EasyRpcServer instance may connect up to 1 other EasyRpcServer instance by creating a server_proxy per namespace. The target instance should not be a child of the instance connecting(i.e loop)
- An EasyRpcServer can recive n connections from other EasyRpcServer server proxies into a single namespace. 

<br>

####  Clustering Patterns
<br>

    # Chaining
    A(pub) <-- B(pub) <-- C(pub) <-- D(pub)

<br>

    # Forking
    A(pub) <-- B(pub)
    A(pub) <-- C(pub)
    A(pub) <-- D(pub)

<br>

    # Ring
    A(left) <-- B(left) <-- C(left)
    A(right) --> C(right) --> B(right)
    
    # create ring
    A.create_namespace_group('ring', 'left', 'right')
    B.create_namespace_group('ring', 'left', 'right')
    C.create_namespace_group('ring', 'left', 'right')



- Each base patterns allow for further forking / chains off the initial nodes of the cluster within the constraints.
<br>

- Each namespace-node within the cluster will have access to every other node(namespace) registered functions. 
<br>

- The path a node takes to reach a function is relative to where the node registered. 

<br>
Example: <br>

     A(pub) <-- B(pub) <-- C(pub) <-- D(pub)

D can access functions on A:

    D -> C
    C -> B
    B -> A

<br>

Connection Interuption

    D -> C
    C # BREAK # B
    B -> A

- C dectects connection is missing, the next proxy probes will remove functions specfic to B & A within the namespace, then propgating update D.
<br>

- B dectects connection is missing, the next proxy probes will remove functions specfic to C & D within the namespace, then propgating update A.

Namespace Groups, discussed next, can help to address these connection interuption concerns. 

## Namespace Groups 
A EasyRpcServer may group two or more namespaces into a single namespace group, providing a single namespace for accessing functions in the group member namespaces. 

### Features / Considerations:
- Functions registered to namespace groups automatically register within the member namespaces
- Namespaces do not allow for duplicate functions, but namespace groups may contain namespaces with same-name functions 
- Namepsaces within namespace groups may consist of local / proxy functions
- Function calls from a namespace group use the first function with the matching name, a duplicates amoungst members are used if the connection to the first function namespace is lost / un-registered.
- Namespace Group appears like a single Namepsace. If a SERVER proxy connects, all member functions are shared to the connecting Proxy, and all discovered functions are updated in all member namespaces. 

### Use Cases
Ring Pattern - Map multiple paths to same functions

    Left  - A <- B <- C
    Right - A -> C -> B 
    Namespace Group ('ring', 'left', 'right')
<br>

    # Server A - port 8220

    server = FastAPI()
    server_a = EasyRpcServer(server, '/ws/server_a', server_secret='abcd1234')
    server_a.create_namespace_group('ring', 'left', 'right')

    @server_a.origin(namespace='ring')
    def a_func(a):
        return {'a': a}

    @server.on_event('startup)
    async def setup():
        def delay_proxy_start():
            # sleep to allow other servers to start
            await asyncio.sleep(15)

            await server_a.create_server_proxy(
                0.0.0.0, 8222, '/ws/server_a', server_secret='abcd1234', namespace='right'
            )
        asyncio.create_task(delay_proxy_start())

<br>

    # Server B - port 8221
    server = FastAPI()
    server_b = EasyRpcServer(server, '/ws/server_b', server_secret='abcd1234')
    server_b.create_namespace_group('ring', 'left', 'right')

    @server_a.origin(namespace='ring')
    def b_func(b):
        return {'b': b}
    
    @server.on_event('startup)
    async def setup()
        await server_b.create_server_proxy(
            0.0.0.0, 8220, '/ws/server_a', server_secret='abcd1234', namespace='left'
        )
<br>

    # Server C - port 8222
    server = FastAPI()
    server_c = EasyRpcServer(server, '/ws/server_c', server_secret='abcd1234')
    server_c.create_namespace_group('ring', 'left', 'right')

    @server_a.origin(namespace='ring')
    def c_func(c):
        return {'c': c}
    
    @server.on_event('startup)
    async def setup()
        await server_c.create_server_proxy(
            0.0.0.0, 8221, '/ws/server_b', server_secret='abcd1234', namespace='left'
        )


All functions in EasyRpcServer A, B, C are registered to both left and right namespaces via ring Namespace Group.  

Server A has two paths to functions on Server B & C 

    A -> C -> B
    A -> B -> C

Server B has two paths to functions on Server A & C 

    B -> A -> C
    B -> C -> A

Server C has two paths to functions on Server B & C 

    C -> B -> A
    C -> A -> B

<br><br>

Simple Grouping and 1 Proxy Connection with single decorator

    Public  - A <- B <- C
    Private - A <- D <- E <- F
    Open - A -> G -> H
    Namespace Group ('all', 'Public', 'Private', 'Open')

    @server.origin(namespace='all')
    def func(a, b, c=10):
        return [a, b, c]

A standard proxy connection provides access to 1 namespace, Namespace Groups can provide two or more namespaces with the same connection. 

    all = await EasyRpcProxy.create(
        '0.0.0.0', 
        8220, 
        '/ws/easy', 
        server_secret='abcd1234',
        namespace='all'
    )

## Under the hood 
easyrpc is made easy via [fastapi](https://github.com/tiangolo/fastapi) for handling server side websocket communciation, [aiohttp](https://github.com/aio-libs/aiohttp) ClientSessions for the client-side websocket communication,  [makefun](https://github.com/smarie/python-makefun) along with some standard library 'inspect' magic  for translating origin functions into proxy-useable functions with parameter validation, and lastly [pyjwt](https://github.com/jpadilla/pyjwt) for authentication & encryption.

Registered functions are made available as callables which return co-routines and thus 'awaitable' to the remote-endpoints, this is true for both async and non-async registered functions. Due to this, the functions must be awaited within a running event_loop. When called, the input parameters are verified via the origin functions signature. 

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