from easyrpc import EasyRpcServer
from fastapi import FastAPI

# Server C - port 8222
server = FastAPI()
server_c = EasyRpcServer(server, '/ws/server_c', server_secret='abcd1234')

@server_c.origin(namespace='public')
def c_func(c):
    return {'c': c}

@server.on_event('startup)
async def setup()
    await server_c.create_server_proxy(
        0.0.0.0, 8220, '/ws/server_b', server_secret='abcd1234', namespace='public'
    )