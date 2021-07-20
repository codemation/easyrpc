from fastapi import FastAPI
from easyrpc.server import EasyRpcServer

server = FastAPI()

@server.on_event('startup')
async def setup():
    cluster_a = EasyRpcServer(server, '/ws/cluster', server_secret='abcd1234')

    @cluster_a.origin(namespace='shared')
    async def cluster_a_func(data: dict):
        return data