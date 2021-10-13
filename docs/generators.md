## Generators
easyrpc can proxy registered generators & async generators with the same constraints as registered functions.

!!! NOTE Constraints
    input arguments  / return values should be pickable objects


Like registered functions, normal generators are converted into async generators at the proxy and must be iterated over using 'async for' or await generator.asend(None)


#### EasyRpcServer
```python
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

```
#### EasyRpcProxy
```python
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
    private_generator = await private['private_generator'](
        [1, 2, 'a', 'b', 3, 4]
    )
    async for item in private_generator:
        print(f"async for {item}")
    
    public_generator = await public['public_generator'](
        [1, 2, 'a', 'b', 3, 4]
    )
    
    while True:
        try:
            result = await public_generator.asend(None)
            print(f"asend result: {result}")
        except StopAsyncIteration:
            break
            
asyncio.run(main())
```