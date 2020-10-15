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

    good_func_c = p.proxy_funcs['good_func_c']

    result = await good_func_c('a', 'b', 'c')
asyncio.run(main())
        