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
    
asyncio.run(main())