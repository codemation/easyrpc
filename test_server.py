from fastapi import FastAPI
from easyrpc.server import EasyRpcServer

server = FastAPI()

ws_server_a = EasyRpcServer(server, '/ws/server_a', server_secret='abcd1234')

ws_server_b = EasyRpcServer(server, '/ws/server_b', server_secret='abcd1234')

@ws_server_a.orgin
def good_func_a(a, b, c):
    print(f"good_func_a {a} {b} {c}")
    return {"good_func_a": [a, b, c]}

@ws_server_b.orgin
def good_func_b(a, b, c):
    print(f"good_func_b {a} {b} {c}")
    return {"good_func_b": [a, b, c]}

# Registered to both servers
@ws_server_a.orgin
@ws_server_b.orgin
def good_func_c(a, **kw):
    print(f"good_func_c {a} {kw}")
    return {"good_func_c": [a, kw]}
