from fastapi import FastAPI
from easyrpc.server import EasyRpcServer

server = FastAPI()

@server.on_event('startup')
async def setup():
    cluster_b = EasyRpcServer(server, '/ws/cluster', server_secret='abcd1234')

    @cluster_b.origin(namespace='shared')
    async def cluster_b_func(data: dict):
        return data

    # connect cluster_b -> cluster_a on shared namespace
    await cluster_b.create_server_proxy(
        '0.0.0.0', 
        8320, 
        '/ws/cluster',
        server_secret='abcd1234', 
        namespace='shared'
    )