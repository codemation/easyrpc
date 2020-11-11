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