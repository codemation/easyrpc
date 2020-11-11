from easyrpc import EasyRpcServer
from fastapi import FastAPI

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