from easyrpc import EasyRpcServer
from fastapi import FastAPI

server = FastAPI()
server_a = EasyRpcServer(server, '/ws/server_a', server_secret='abcd1234')

@server_a.origin(namespace='public')
def a_func(a):
    return {'a': a}