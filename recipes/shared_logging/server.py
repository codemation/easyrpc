# central logging server

import logging
from fastapi import FastAPI
from easyrpc.server import EasyRpcServer

logging.basicConfig()

server = FastAPI()

@server.on_event('startup')
async def setup():

    logger = logging.getLogger()

    rpc_server = EasyRpcServer(server, '/ws/server', server_secret='abcd1234', debug=True)

    rpc_server.register_logger(logger, namespace='logger')