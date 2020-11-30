# share logging with another server

from fastapi import FastAPI
from easyrpc.server import EasyRpcServer

server = FastAPI()

@server.on_event('startup')
async def setup():
    #server
    ws_server_b = EasyRpcServer(server, '/ws/server', server_secret='efgh1234')

    logger = await ws_server_b.create_server_proxy_logger(
        '0.0.0.0', 8220, '/ws/server', server_secret='abcd1234', namespace='logger'
    )

    await logger.warning(f"ws_server_b - starting with id {ws_server_b.server_id}")