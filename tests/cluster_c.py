from fastapi import FastAPI
from easyrpc.server import EasyRpcServer

server = FastAPI()

@server.on_event('startup')
async def setup():
    cluster_c = EasyRpcServer(server, '/ws/cluster', server_secret='abcd1234')

    @cluster_c.origin(namespace='shared')
    async def cluster_c_func(data: dict):
        return data

    # connect cluster_c -> cluster_b on shared namespace
    await cluster_c.create_server_proxy(
        '0.0.0.0', 
        8321, 
        '/ws/cluster',
        server_secret='abcd1234', 
        namespace='shared'
    )