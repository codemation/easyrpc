from easyrpc import EasyRpcServer
from fastapi import FastAPI

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