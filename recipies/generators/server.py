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